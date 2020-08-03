# thumbnail_maker.py
import time
import os
import logging
from urllib.parse import urlparse
from urllib.request import urlretrieve

from queue import Queue
from threading import Thread

import multiprocessing

import PIL
from PIL import Image

FORMAT = "[%(threadName)s, %(asctime)s, %(levelname)s] %(message)s"
logging.basicConfig(filename='logfile.log', level=logging.DEBUG, format=FORMAT)

class ThumbnailMakerService(object):
    def __init__(self, home_dir='.'):
        self.home_dir = home_dir
        self.input_dir = self.home_dir + os.path.sep + 'incoming'
        os.makedirs(self.input_dir, exist_ok=True)
        self.output_dir = self.home_dir + os.path.sep + 'outgoing'
        os.makedirs(self.output_dir, exist_ok=True)

        self.img_list = [] # has to be pickable

    def download_image(self, dl_queue=None):
        while not dl_queue.empty():
            try:
                url = dl_queue.get(block=False)
                # download each image and save to the input dir 
                img_filename = urlparse(url).path.split('/')[-1]
                urlretrieve(url, self.input_dir + os.path.sep + img_filename)
                self.img_list.append(img_filename)
                
                dl_queue.task_done()
            except Queue.Empty:
                pass

    def resize_image(self, filename):
        target_sizes = [32, 64, 200]
        orig_img = Image.open(self.input_dir + os.path.sep + filename)
        for basewidth in target_sizes:
            img = orig_img
            # calculate target height of the resized image to maintain the aspect ratio
            wpercent = (basewidth / float(img.size[0]))
            hsize = int((float(img.size[1]) * float(wpercent)))
            # perform resizing
            img = img.resize((basewidth, hsize), PIL.Image.LANCZOS)
            
            # save the resized image to the output dir with a modified file name 
            new_filename = os.path.splitext(filename)[0] + \
                '_' + str(basewidth) + os.path.splitext(filename)[1]
            img.save(self.output_dir + os.path.sep + new_filename)

        os.remove(self.input_dir + os.path.sep + filename)

    def make_thumbnails(self, img_url_list):
        logging.info("START make_thumbnails")
        pool = multiprocessing.Pool()
        start = time.perf_counter()

        dl_queue = Queue() # self.dl_queue is not pickable so we create an object to pass

        for img_url in img_url_list:
            dl_queue.put(img_url)
        
        num_dl_threads = 12
        for _ in range(num_dl_threads):
            t = Thread(target=self.download_image, args=(dl_queue, ))
            t.start()

        dl_queue.join() # block the main thread till all downloads are complete.
        
        pool.map(self.resize_image, self.img_list)

        end = time.perf_counter()
        pool.close()
        pool.join()

        logging.info("END make_thumbnails in {} seconds".format(end - start))
    