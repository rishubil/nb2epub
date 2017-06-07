#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import requests
import json
import time
from bs4 import BeautifulSoup
import pypandoc
import re
import os

DEBUG = False
# DEBUG = True

def print_help():
    print("USAGE: python nb2epub.py BLOG_ID CAGETORY_NUMBER TITLE")
    sys.exit(-1)

def print_error(error_msg):
    print(error_msg)
    sys.exit(-1)

def get_url(url):
    time.sleep(0.1) # delay for preventing block
    if DEBUG:
        print("DEBUG: Request GET for {url}".format(url=url))
    return requests.get(url)

def get_list_url(blog_id, category_number, page=1):
    return "http://blog.naver.com/PostTitleListAsync.nhn?blogId={blog_id}&viewdate=&currentPage={page}&categoryNo={category_number}&parentCategoryNo=&countPerPage=30".format(blog_id=blog_id, category_number=category_number, page=page)

def get_list(blog_id, category_number):
    print("Gathering posts...")
    posts = []
    page = 1
    while True:
        list_url = get_list_url(blog_id, category_number, page)
        list_r = get_url(list_url)
        if list_r.status_code >= 400:
            print_error("Cannot get post list ({code}): {url}".format(url=list_url, code=list_r.status_code))
        list_json = json.loads(list_r.text.replace("\\'", "'"), encoding=list_r.encoding)

        if not list_json["postList"]:
            print("Gathering posts...[{0}/{1}]".format(len(posts), int(list_json["totalCount"])))
            return posts

        posts += list_json["postList"]

        if len(posts) >= int(list_json["totalCount"]):
            print("Gathering posts...[{0}/{1}]".format(len(posts), int(list_json["totalCount"])))
            return posts
        print("Gathering posts...[{0}/{1}]".format(len(posts), int(list_json["totalCount"])))

        page += 1

def get_post_contents_url(blog_id, category_number, post_number):
    return "http://blog.naver.com/PostView.nhn?blogId={blog_id}&logNo={post_number}&categoryNo={category_number}&parentCategoryNo=0&viewDate=&currentPage=1&postListTopCurrentPage=&from=postList&userTopListOpen=true&userTopListCount=30&userTopListManageOpen=false&userTopListCurrentPage=1".format(blog_id=blog_id, category_number=category_number, post_number=post_number)

def parse_contents(funcs):
    try:
        if funcs:
            return funcs[0]()
        else:
            raise AttributeError()
    except AttributeError:
        parse_contents(funcs[1:])

def get_post_contents(blog_id, category_number, post):
    post_title = post["title"]
    post_url = get_post_contents_url(blog_id, category_number, post["logNo"])
    post_r = get_url(post_url)
    if post_r.status_code >= 400:
        print_error("Cannot get post contents ({code}): {url}".format(url=post_url, code=post_r.status_code))

    post_s = BeautifulSoup(post_r.content.decode('ms949', 'ignore'), "lxml")
    try:
        post_contents = str(parse_contents([
            lambda: post_s.find(id="postViewArea").div,
            lambda: post_s.find(class_="__se_component_area").div
        ]))
    except:
        print_error("Cannot parse post: {url}".format(url=post_url))

    post_contents = re.sub(r"(class|id|onclick)=\".*?\"\s*", "", post_contents)
    post_contents = re.sub(r"[^\";]*font-family:.*?;", "", post_contents)
    post_contents = re.sub(r"<br/>", "", post_contents)

    return post_contents


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print_help()
    blog_id = sys.argv[1]
    category_number = sys.argv[2]
    title = sys.argv[3]

    rev_posts = get_list(blog_id, category_number)
    posts = reversed(rev_posts)
    count_posts = len(rev_posts)

    contents = ""
    for i, post in enumerate(posts):
        print("Download post [{0}/{1}]...".format(i + 1, count_posts))
        post_contents = get_post_contents(blog_id, category_number, post)
        contents += post_contents

    print("Convert posts to file...")
    pypandoc.convert_text(contents, 'epub', format='html', outputfile="{title}.epub".format(title=title))
    print("Done.")
