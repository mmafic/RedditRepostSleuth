import argparse
import sys
import threading
from time import sleep
from datetime import datetime

from redditrepostsleuth.celery.tasks import find_matching_images_task
from redditrepostsleuth.common.logging import log
from redditrepostsleuth.db import db_engine
from redditrepostsleuth.db.uow.sqlalchemyunitofworkmanager import SqlAlchemyUnitOfWorkManager
from redditrepostsleuth.model.hashwrapper import HashWrapper
from redditrepostsleuth.service.CachedVpTree import CashedVpTree
from redditrepostsleuth.service.commentmonitor import CommentMonitor
from redditrepostsleuth.service.imagerepost import ImageRepostProcessing
from redditrepostsleuth.service.maintenanceservice import MaintenanceService
from redditrepostsleuth.service.postIngest import PostIngest
from redditrepostsleuth.service.requestservice import RequestService
from redditrepostsleuth.util.helpers import get_reddit_instance

sys.setrecursionlimit(10000)

if __name__ == '__main__':
    """
    tree = CashedVpTree(SqlAlchemyUnitOfWorkManager(db_engine))
    start = datetime.now()
    tree2 = tree.get_tree
    delta = datetime.now() - start
    print('Tree built in {} seconeds'.format(str(delta.seconds)))
    sys.exit()
    

    wrapper = HashWrapper()
    wrapper.post_id = 'amv5ru'
    wrapper.image_hash = '78f460f9e0b968bc6068b8419f0c4c3438fce0d3c899fcb8b8509c004c1c7634'

    r = find_matching_images_task.apply_async(queue='repost', args=(wrapper,)).get()
    """

    parser = argparse.ArgumentParser(description="A Tool to monitor and respond to reposted content on Reddit")
    parser.add_argument('--ingestposts', action='store_true', help='Enables the post import agent')
    parser.add_argument('--ingestcomments', action='store_true', help='Enables the comment import agent')
    parser.add_argument('--summons', action='store_true', help='Enables agent to monitor for and respond to summons')
    parser.add_argument('--repost', action='store_true', help='Enables agent that scans database for reposts')
    parser.add_argument('--imagehashing', action='store_true', help='Enables agent that calculates and saves hashes of posts')
    parser.add_argument('--deleted', action='store_true', help='Enables agent that that prunes deleted posts')
    parser.add_argument('--crosspost', action='store_true', help='Process Cross Posts in Backgroun')
    args = parser.parse_args()

    threads = []
    hashing = ImageRepostProcessing(SqlAlchemyUnitOfWorkManager(db_engine), get_reddit_instance())
    repost_service = RequestService(SqlAlchemyUnitOfWorkManager(db_engine), hashing, get_reddit_instance())
    comments = CommentMonitor(get_reddit_instance(), repost_service, SqlAlchemyUnitOfWorkManager(db_engine))
    if args.ingestposts:
        log.info('Starting Post Ingest Agent')
        ingest = PostIngest(get_reddit_instance(), SqlAlchemyUnitOfWorkManager(db_engine))
        threading.Thread(target=ingest.ingest_new_posts, name='Post Ingest').start()
        #threading.Thread(target=ingest.check_cross_posts, name='Post Ingest').start()
        #threading.Thread(target=ingest._flush_submission_queue_test, name='Flush Ingest').start()

    if args.ingestcomments:
        log.info('Starting Comment Ingest Agent')
        threading.Thread(target=comments.ingest_new_comments, name='CommentIngest').start()
        threading.Thread(target=comments.process_comment_queue, name='CommentIngestQueue').start()

    if args.imagehashing:
        log.info('Starting Hashing Agent')
        threading.Thread(target=hashing.generate_hashes, name="Hashing").start()
        threading.Thread(target=hashing.process_hash_queue, name="HashingFlush").start()

    if args.repost:
        log.info('Starting Repost Agent')
        if hashing is None:
            hashing = ImageRepostProcessing(SqlAlchemyUnitOfWorkManager(db_engine), get_reddit_instance())
        threading.Thread(target=hashing.process_repost_celery_new, name='Repost').start()
        #threading.Thread(target=hashing.process_repost_queue, name='Repost Queue').start()

    if args.deleted:
        maintenance = MaintenanceService(SqlAlchemyUnitOfWorkManager(db_engine))
        threading.Thread(target=maintenance.clear_deleted_images, name='Deleted Cleanup').start()

    if args.summons:
        if hashing is None:
            hashing = ImageRepostProcessing(SqlAlchemyUnitOfWorkManager(db_engine), get_reddit_instance())


        threading.Thread(target=comments.monitor_for_summons, name='SummonsThread').start()
        threading.Thread(target=comments.handle_summons).start()



    while True:
        """
        log.info('Running Threads:')
        for thrd in threading.enumerate():
            log.info(thrd.name)
        """
        sleep(5)