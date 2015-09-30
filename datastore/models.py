import json
from time import localtime
from datetime import datetime

from google.appengine.ext import ndb

from config.config import articles_api_version

__author__ = 'lorenzo'


class WebResource(ndb.Model):
    """
    Indexed Web pages and single entries of a crawled RSS-feed
    """
    title = ndb.StringProperty()
    abstract = ndb.TextProperty()
    url = ndb.StringProperty()
    stored = ndb.DateTimeProperty(default=datetime(*localtime()[:6]))
    published = ndb.DateTimeProperty(default=None)

    @classmethod
    def dump_from_json(cls, j):
        """
        Store a WebResource from a JSON object
        :param j: a JSON
        :return: a WebResource
        """
        print j
        j = json.loads(j)
        if cls.query().filter(cls.url == j['url']).count() == 0:
            m = WebResource()
            m.title = j['title']
            m.abstract = j['abstract']
            m.url = j['url']
            m.slug = j['keyword']
            obj = m.put()
            index = Indexer(keyword=j['key'], webres=obj)
            index.put()
            return obj

    @classmethod
    def store_feed(cls, entry):
        """
        Store RSS-feed entry coming from feedparser
        """
        if cls.query().filter(cls.url == str(entry['link'])).count() == 0:
            # define the WebResource
            item = WebResource()
            from unidecode import unidecode
            try:
                item.title = unidecode(unicode(" ".join(entry['title'].split())))
            except:
                item.title = " ".join(entry['title'].encode('ascii', 'replace').split())

            print item.title
            item.url = str(entry['link'])
            item.stored = datetime(*localtime()[:6])
            item.published = datetime(*entry['published_parsed'][:6]) if 'published_parsed' in entry.keys() else item.stored

            try:
                item.abstract = unidecode(unicode(" ".join(entry['summary'].strip().split()))) if entry['summary'] is not None else ""
            except:
                item.abstract = " ".join(entry['summary'].strip().encode('ascii', 'replace').split()) if entry['summary'] is not None else ""

            i = item.put()

            try:
                if len(entry.media_content) != 0:
                    print "has media"
                    for obj in entry.media_content:
                        # store image or video as child
                        if cls.query().filter(cls.url == obj.url).count() == 0:
                            m = WebResource(url=obj.url, published=item.published, parent=i.get(), title='', abstract='')
                            m.put()
                            print "media stored"
            except:
                pass

            return i

    @classmethod
    def store_tweet(cls, twt):
        """
        Store a Tweet, its media and its containing link from the Twitter API
        """
        url = 'https://twitter.com/' + str(twt.GetUser().screen_name) + '/status/' + str(twt.GetId())
        try:
            media = twt.media[0]['media_url'] if isinstance(twt.media, list) and len(twt.media) != 0 else None
        except Exception:
            media = twt.media['media_url'] if isinstance(twt.media, dict) and 'media_url' in twt.media.keys() else None
        except:
            media = None

        link = twt.urls[0].expanded_url if len(twt.urls) != 0 else None
        text = twt.text if len(twt.text) > 35 else None
        import time
        published = str(twt._created_at)[:19] + str(twt._created_at)[25:]
        published = time.strptime(published, '%a %b %d %H:%M:%S %Y')
        published = datetime(*published[:6])

        if text:
            if cls.query().filter(cls.url == url).count() == 0:
                # store tweet
                w = WebResource(url=url, published=published, title=str(twt._id), abstract=text)
                k = w.put()
                print "Tweet stored" + str(k)
                if media:
                    if cls.query().filter(cls.url == media).count() == 0:
                        # store image or video as child
                        m = WebResource(url=media, published=published, parent=k, title='', abstract='')
                        m.put()
                        print "media stored"
                if link:
                    if cls.query().filter(cls.url == link).count() == 0:
                        # store contained link as child
                        l = WebResource(url=link, published=published, parent=k, title='', abstract='')
                        l.put()
                        print "link stored"

                return w

    def dump_to_json(self):
        """
        make property values of an instance JSON serializable
        """
        result = {
            "uuid": self.key.id()
        }
        for prop, value in self.to_dict().items():
            # If this is a key, you might want to grab the actual model.
            if prop == 'url':
                result[prop] = value
                result['keywords_url'] = articles_api_version("04") + '?url=' + value
            if isinstance(self, ndb.Model):
                if isinstance(value, datetime):
                    result[prop] = value.isoformat()
                    continue
                elif value is None:
                    result[prop] = None
                    continue
                from unidecode import unidecode
                result[prop] = unidecode(unicode(value.strip()))

        return result

    def get_indexers(self):
        """
        For a given WebResource, get the keywords stored in Indexer for that resource
        :return: a dict() with a "keywords" property, with value is an array of keyword objects
        """
        query = Indexer.query().filter(Indexer.webres == self.key)
        if query.count() != 0:
            results = {
                "keywords": [
                    {
                        "value": q.keyword,
                        "slug": q.keyword.replace(" ", "+"),
                        "related_urls": articles_api_version("04") + 'keywords?keyword=' + q.keyword
                    }
                    for q in query
                ],
                "url": self.url,
                "uuid": self.key.id()
            }
            return results
        return {
            "keywords": None
        }


class Indexer(ndb.Model):
    """
    A map between keywords and urls
    """
    keyword = ndb.StringProperty()
    webres = ndb.KeyProperty(kind=WebResource)

    @classmethod
    def get_webresource(cls, kwd):
        """
        For a given keyword, get the Web Resources stored in Indexer
        :param kwd: a keyword
        :return: a list of WebResource
        """
        # TO-DO: check if the keyword belong to taxonomy.projectchronos.eu/concept/c
        query = Indexer.query().filter(Indexer.keyword == kwd)
        if query.count() != 0:
            results = [q.webres.get() for q in query]
            return results
        return []


class N3Cache(ndb.Model):
    """
    Cache Dbpedia N3.
    id=url
    """
    # id=url
    n3 = ndb.TextProperty()
    updated = ndb.DateTimeProperty(default=datetime(*localtime()[:6]))

    def check_if_stored(self):
        pass

    def check_if_modified(self):
        pass