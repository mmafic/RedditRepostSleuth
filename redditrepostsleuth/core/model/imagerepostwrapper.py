from redditrepostsleuth.core.db.databasemodels import MemeTemplate
from redditrepostsleuth.core.model.repostwrapper import RepostWrapper


class ImageRepostWrapper(RepostWrapper):
    def __init__(self):
        super().__init__()

        self.total_search_time: float = None
        self.index_search_time: float= None
        self.total_searched: int = 0
        self.meme_template: MemeTemplate = None

    def to_dict(self):
        r = {
            'total_search_time': self.total_search_time,
            'index_search_time': self.index_search_time,
            'index_size': self.total_searched,
            'meme_template': self.meme_template.to_dict() if self.meme_template else None
        }
        return {**r, **super(ImageRepostWrapper,self).to_dict()}

    def __repr__(self):
        return f'Checked Post: {self.checked_post.post_id} - Matches: {len(self.matches)} - Meme Template: {self.meme_template} - Search Time: {self.total_search_time}'