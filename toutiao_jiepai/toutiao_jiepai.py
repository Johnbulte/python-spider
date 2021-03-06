# -*- coding: utf-8 -*-
"""
Created on Tue Jul 17 14:58:53 2018

@author: Administrator
"""

import requests
from requests.exceptions import RequestException
from urllib.parse import urlencode #用于在网址链接中加入参数
import json
from bs4 import BeautifulSoup
import re
import os
from hashlib import md5
from multiprocessing import Pool
import time

def get_page_index(offset, keyword):
    '''
    Desc:
        抓取通过offset实现Ajax异步加载的URL，返回当前offset的内容
    param:
        offset -- 为了实现Ajax异步加载，使用offset实现动态分页
        keyword -- 搜索用的关键词
    return:
        res.text -- 当前offset的requests.text内容
    '''
    url_param ={
        'offset': offset,
        'format': 'json',
        'keyword': keyword,
        'autoload': 'true',
        'count': '20',
        'cur_tab': 1,
        'from': 'search_tab'
    }
    url = 'https://www.toutiao.com/search_content/?' + urlencode(url_param)
    try:
        res = requests.get(url)
        res.encoding = 'utf-8'
        #返回的状态码是整型
        if res.status_code == 200:
            return res.text
        return None
    except RequestException:
        print("请求索引页面出错")
        return None

    
def parse_page_index(html):
    '''
    Desc:
        解析当前offset的requests.text内容
    param:
        html -- 当前offset的res.text内容
    return:
        item.get('article_url') -- 组图中的文章链接
    '''
    data = json.loads(html) #将网页的js数据格式转换为json
    if data and 'data' in data.keys():
        for item in data.get('data'):
            if item.get('article_url') != None:
                yield item.get('article_url')


def get_page_detail(url):
    '''
    Desc:
        获取每一个组图详情页连接的内容
    param:
        url -- 组图详情页的链接
    return:
        res.text -- 每一个组图详情页链接的res.text内容
    '''
    try:
        headers = {
            'user-agent':'Mozilla/5.0'
        }
        res = requests.get(url, headers=headers)
        res.encoding = 'utf-8'
        #返回的状态码是整型
        if res.status_code == 200:
            return res.text
        return None
    except RequestException:
        print("请求详情页面出错")
        return None


def download_img(url, file_name):
    '''
    Desc:
        下载图片到指定的文件file_name中
    param:
        url -- 每一张图片的url
    '''
    print("正在下载", url)
    try:
        headers = {
            'user-agent':'Mozilla/5.0'
        }
        res = requests.get(url, headers=headers)
#         res.encoding = 'utf-8'
        #返回的状态码是整型
        if res.status_code == 200:
            
            if not os.path.exists(file_name):
                with open(file_name, 'wb') as f:
                    f.write(res.content) #图片信息为二进制数据，所以为调用content方法
                    f.close() 
        return None
    except RequestException:
        print("下载图片出错")
        return None
    
i=1 #图片名称索引   
def parse_page_detail(html, url, file_name):
    '''
    Desc:
        解析组图详情页的内容，返回组图详情页的标题，详情页里面的图片，详情页的url
    param:
        html -- 组图详情页的html内容 
        url -- 组图详情页的链接
        file_name -- 存储图片的目录
    return:
        一个字典 -- 
        {
            'title': title, #街拍详情页的标题
            'images':images, #街拍详情页的组图图片
            'url':url #街拍详情页的网页链接
        }
    '''
    soup = BeautifulSoup(html, 'lxml')
    title = soup.select('title')[0].text
    #使用正则表达式提取json数据
    img_pattern = re.compile('gallery: JSON\\.parse\\("(.*?)"\\),', re.S)
    result = re.search(img_pattern, html)
    if result != None:
        data = (result.group(1))
        #由于json要求键值都必须时双引号的字符串，而且这里做了反爬虫处理，因此，我们要删除多余的转义字符\\
        data = data.replace("\\","") 
        #将去除多余的转义字符的字符串转换为json格式的字典存储
        data = json.loads(data)
        if data and 'sub_images' in data.keys():
            sub_images = data.get('sub_images')
            images = [item.get('url') for item in sub_images]
            for image in images:
                global i #声明图片名称索引为全局变量
                image_name = '{0}{1}{2}'.format(file_name, str(i), '.jpg')
                download_img(image, image_name)
                i += 1
            return {
                'title': title, #街拍详情页的标题
                'images':images, #街拍详情页的组图图片
                'url':url #街拍详情页的网页链接
            }


def main(offset):
    '''
    Desc:
        抓取头条街拍组图，将每一张图片存储到目录path下，并将组图标题，
        每一张图片的链接，组图详情页的链接存储到result.json中
    param:
        offset -- Ajax动态加载的分页偏置
    '''
    #在当前路径images路径下存储图片，图片命名为md5的格式+jpg
    keyword = '街拍' #可修改搜索关键字
    path = "I:/文档/爬虫数据/images" #图片存储目录
    if not os.path.exists(path):
        os.mkdir(path)
    file_name = '{0}/'.format(path)
    html = get_page_index(offset, keyword)
    #遍历每一个详情页
    for url in parse_page_index(html):
        #获得每一个详情页html内容
        html = get_page_detail(url)
        if html:
            #解析详情页中的图片
            result = parse_page_detail(html, url, file_name) #返回一个带有键title,images,url的字典
            #把带有键title,images,url的字典存储到result.json中
            with open('result.json', 'a', encoding='utf-8') as f:
                f.write(json.dumps(result, ensure_ascii=False) + '\n')

if __name__ == '__main__':
    start_time = time.time()
    pool = Pool()
    group_start = 0
    group_end = 1  #修改此处来抓取Ajax加载的图片
    groups = [x*20 for x in range(group_start, group_end)] 
    pool.map(main, groups)
    end_time = time.time()
    print("cost time : %.2fs" % (end_time-start_time))
