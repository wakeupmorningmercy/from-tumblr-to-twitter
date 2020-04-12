from twitter import Twitter, OAuth
from PIL import Image

import xml.etree.ElementTree as ET

import glob
import re
import os


def init():
    CONSUMER_KEY = ""
    CONSUMER_SECRET = ""
    ACCESS_TOKEN = ""
    ACCESS_TOKEN_SECRET = ""

    my_auth = OAuth(token=ACCESS_TOKEN,
                    token_secret=ACCESS_TOKEN_SECRET,
                    consumer_key=CONSUMER_KEY,
                    consumer_secret=CONSUMER_SECRET)

    t = Twitter(auth=my_auth)
    t_up = Twitter(domain='upload.twitter.com', auth=my_auth)

    return t, t_up


# https://stackoverflow.com/questions/753052/strip-html-from-strings-in-python
# [^<] works too
def strip_html_tags(text):
    return re.sub('<[^<]+?>', '', text).replace('\n', ' ')


def ensure_tweet_limit(caption, tags, date):
    TWEET_LIMIT = 280

    # strip nontags
    stripped_tags = (
        ' #'.join(list(map(lambda tag: tag.replace('-', '').replace(' ', ''),
                           tags)))
    )
    stripped_caption = strip_html_tags(caption)

    # status = f"{caption} #{stripped_tags} {date}"
    # if len(status) <= TWEET_LIMIT:
    #     return status

    status = f"{stripped_caption} #{stripped_tags} {date}"
    if len(status) <= TWEET_LIMIT:
        return status

    status = f"{stripped_caption} #{stripped_tags}"
    if len(status) <= TWEET_LIMIT:
        return status

    suffix = ' #wakeupmorning'
    status = (
        f"{stripped_caption[:TWEET_LIMIT-len(suffix)]}"
        f"{suffix}"
    )
    return status


# https://stackoverflow.com/questions/273946/how-do-i-resize-an-image-using-pil-and-maintain-its-aspect-ratio/273962
def resize(filename, img, basewidth):
    wpercent = (basewidth/float(img.size[0]))
    hsize = int((float(img.size[1])*float(wpercent)))
    img = img.resize((basewidth, hsize), Image.ANTIALIAS)
    new_file_name = f'{filename}_{basewidth}.jpg'
    img.save(new_file_name)

    size = os.stat(new_file_name).st_size
    print(f'resize: {new_file_name} {size}B')
    return new_file_name, size


def upload(t, t_up, media_file, caption, tags, date):
    # Tweet must not have more than 4 mediaIds.
    MAX_MEDIAS = 4
    MAX_PICTURE_BYTES = 5120000

    files = glob.glob(f'./media/{media_file}*.jpg')
    media_ids = []
    for file in files[:MAX_MEDIAS]:
        size = os.stat(file).st_size
        if size > MAX_PICTURE_BYTES:
            file_name = os.path.splitext(file)[0]
            im = Image.open(file)
            new_size_x = im.size[0] - 100
            while size > MAX_PICTURE_BYTES:
                new_file_name, size = resize(file_name, im, new_size_x)
                new_size_x -= 100
        else:
            new_file_name = file

        with open(new_file_name, "rb") as imagefile:
            imagedata = imagefile.read()

        id_img = t_up.media.upload(media=imagedata)["media_id_string"]
        media_ids.append(id_img)

    print(media_ids)

    status = ensure_tweet_limit(caption, tags, date)
    print(status)
    t.statuses.update(status=status, media_ids=",".join(media_ids))


def parse():
    tree = ET.parse('posts/posts.xml')
    root = tree.getroot()

    posts = []
    for post in root.iter('post'):
        id = post.get('id')
        timestamp = post.get('unix-timestamp')
        date = post.get('date')
        caption_element = post.find('photo-caption')
        if caption_element is not None:
            caption = caption_element.text
        else:
            caption = 'N/A'

        tags = []
        for tag in post.findall('tag'):
            tags.append(tag.text)

        posts.append({
            'id': id,
            'timestamp': timestamp,
            'date': date,
            'caption': caption,
            'tags': tags
        })

    sorted_posts = sorted(posts, key=lambda p: p['timestamp'])
    return sorted_posts


if __name__ == '__main__':
    t, up = init()

    posts = parse()
    posts_to_process = posts[71:81]
    for post in posts_to_process:
        upload(t, up, post['id'], post['caption'], post['tags'], post['date'])
