import time
from queue import Queue
from typing import List, Tuple

import requests
from celery import group
from distance import hamming
from praw.models import Submission

from redditrepostsleuth.celery import image_hash
from redditrepostsleuth.common.exception import ImageConversioinException
from redditrepostsleuth.common.logging import log
from redditrepostsleuth.db.uow.unitofworkmanager import UnitOfWorkManager
from redditrepostsleuth.model.db.databasemodels import Post
from redditrepostsleuth.model.repostresponse import RepostResponse
from redditrepostsleuth.util import submission_to_post
from redditrepostsleuth.util.imagehashing import generate_dhash, find_matching_images_in_vp_tree, \
    find_matching_images, generate_img_by_url
from redditrepostsleuth.util.vptree import VPTree


class ImageRepostProcessing:

    def __init__(self, uowm: UnitOfWorkManager) -> None:
        self.uowm = uowm
        self.existing_images = [] # Maintain a list of existing images im memory
        self.hash_save_queue = Queue(maxsize=0)


    def generate_hashes_celery(self):
        """
        Collect images from the database without a hash.  Batch them into 100 posts and submit to celery to have
        hashes created
        """
        while True:
            #TODO - Cleanup
            posts = []
            try:
                with self.uowm.start() as uow:
                    posts = uow.posts.find_all_by_hash(None, limit=150)

                jobs = []
                for post in posts:
                    jobs.append(image_hash.s({'url': post.url, 'post_id': post.post_id, 'hash': None, 'delete': False}))

                job = group(jobs)
                log.debug('Starting Celery job with 100 images')
                pending_result = job.apply_async()
                while pending_result.waiting():
                    log.info('Not all tasks done')
                    time.sleep(1)

                result = pending_result.join_native()
                for r in result:
                    self.hash_save_queue.put(r)


            except Exception as e:
                # TODO - Temp wide exception to catch any faults
                log.exception('Error processing celery jobs', exc_info=True)


    def process_hash_queue(self):
        while True:
            results = []
            while len(results) < 150:
                try:
                    results.append(self.hash_save_queue.get())
                except Exception as e:
                    log.exception('Exception with hash queue', exc_info=True)
                    continue

            log.info('Flushing hash queue to database')

            with self.uowm.start() as uow:
                # TODO - Find a cleaner way to deal with this
                for result in results:
                    post = uow.posts.get_by_post_id(result['post_id'])
                    if not post:
                        continue
                    if result['delete']:
                        log.debug('TASK RESULT: Deleting Post %s', result['post_id'])
                        uow.posts.remove(post)
                    else:
                        log.debug('TASK RESULT: Saving Post %s', result['post_id'])
                        post.image_hash = result['hash']
                    uow.commit()

    def find_all_occurrences(self, submission: Submission):
        """
        Take a given Reddit submission and find all matching posts
        :param submission:
        :return:
        """
        try:
            img = generate_img_by_url(submission.url)
            image_hash = generate_dhash(img)
        except ImageConversioinException:
            return RepostResponse(message="I failed to convert the image to a hash :(", status='error')

        with self.uowm.start() as uow:
            existing_images = uow.posts.find_all_images_with_hash()
            occurrences = find_matching_images(existing_images, image_hash)

            # Save this submission to database if it's not already there
            if not uow.posts.get_by_post_id(submission.id):
                log.debug('Saving post %s to database', submission.id)
                post = submission_to_post(submission)
                post.image_hash = image_hash
                uow.posts.add(post)
                uow.commit()

            return RepostResponse(message='I found {} occurrences of this image'.format(len(occurrences)),
                                  occurrences=self._sort_reposts(occurrences),
                                  posts_checked=len(existing_images))

    def clear_deleted_images(self):
        """
        Cleanup images in database that have been deleted by the poster
        """
        # TODO - Move it single function
        while True:
            with self.uowm.start() as uow:
                posts = uow.posts.find_all_by_type('image')
                for post in posts:
                    log.debug('Checking URL %s', post.url)
                    try:
                        r = requests.get(post.url)
                        if r.status_code == 404:
                            log.debug('Deleting removed post (%s)', str(post))
                            uow.posts.remove(post)
                            uow.commit()
                    except Exception as e:
                        log.exception('Exception with deleted image cleanup', exc_info=True)
                        print('')

    def process_reposts(self):
        while True:
            with self.uowm.start() as uow:
                unchecked_posts = uow.posts.find_all_by_repost_check(False, limit=100)
                self.existing_images = uow.posts.find_all_images_with_hash()
                # TODO - Deal with crosspost
                log.info('Building VP Tree with %s objects', len(self.existing_images))
                tree = VPTree(self.existing_images, lambda x,y: hamming(x,y))
                for repost in unchecked_posts:
                    print('Checking Hash: ' + repost.image_hash)
                    repost.checked_repost = True
                    r = find_matching_images_in_vp_tree(tree, repost.image_hash, hamming_distance=10)

                    if len(r) == 1:
                        continue

                    results = self._filter_matching_images(r, repost)
                    results = self._clean_reposts(results)
                    if len(results) > 0:
                        print('Original: http://reddit.com' + repost.perma_link)

                        log.info('Checked Repost - %s - (%s): http://reddit.com%s', repost.post_id, str(repost.created_at), repost.perma_link)
                        log.info('Oldest Post - %s - (%s): http://reddit.com%s', results[0].post_id, str(results[0].created_at), results[0].perma_link)
                        for p in results:
                            log.info('%s - %s: http://reddit.com/%s', p.post_id, str(p.created_at), p.perma_link)

                        repost.repost_of = results[0].id
                    uow.commit()

    def _filter_matching_images(self, raw_list: List[Tuple[int, Post]], post_being_checked: Post) -> List[Post]:
        """
        Take a raw list if matched images.  Filter one ones meeting the following criteria.
            Same Author as post being checked - Gets rid of people posting to multiple subreddits
            If it has a crosspost parent - A cross post isn't considered a respost
            Same post ID as post being checked - The image list will contain the original image being checked
        :param raw_list: List of all matches
        :param post_being_checked: The posts we're checking is a repost
        """
        # TODO - Clean this up
        return [x[1] for x in raw_list if x[1].post_id != post_being_checked.post_id and x[1].crosspost_parent is None and post_being_checked.author != x[1].author]


    def _handle_reposts(self, post: List[Post]) -> List[Post]:
        """
        Take a list of reposts and process them
        :param post: List of Posts
        """
        pass


    def _clean_reposts(self, posts: List[Post]) -> List[Post]:
        """
        Take a list of reposts, remove any cross posts and deleted posts
        :param posts: List of posts
        """
        posts = [post for post in posts if post.crosspost_parent is None]
        posts = self._sort_reposts(posts)
        return posts


    def _sort_reposts(self, posts: List[Post], reverse=False) -> List[Post]:
        """
        Take a list of reposts and sort them by date
        :param posts:
        """
        return sorted(posts, key=lambda x: x.created_at, reverse=reverse)