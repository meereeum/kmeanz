import tensorflow as tf
import numpy as np
from PIL import Image
import random
import itertools
import os


class kmeans():
    def __init__(self, filepath, rounds=2, k=10, scale=False, generate_all=True, outdir=None):
        self.k = k
        if not outdir: # default to parent directory of input
            outdir = os.path.dirname(filepath)
        # basename sans extension
        basename = os.path.splitext(os.path.basename(filepath))[0]
        self.pixels = np.array(Image.open(filepath))

        m, n, cols = self.pixels.shape
        if cols > 3:
            self.pixels = self.pixels[:,:,:3]
        self.n_pixels = m*n
        self.ratio = (255.0/max(m,n) if scale else 1.0) # rescale by max dimension

        idx_lst = [ (j*self.ratio, k*self.ratio) for j in xrange(m) for k in xrange(n) ]
        idx_arr = np.array(idx_lst).reshape((m, n, 2))
        # 2D array = array of [m, n, r, g, b] arrays
        self.arr = np.concatenate((idx_arr, self.pixels), axis=2).\
                    ravel().reshape((m*n,5))

        #centroids = np.array(random.sample(self.arr, self.k), dtype=np.float32)
        #centroids_in, centroids_out = self._build_graph()
        self._build_graph()

        with tf.Session() as sesh:
            sesh.run(tf.initialize_all_variables())
            feed_dict = None # first round initialized with random centroids by tf node
            for i in xrange(rounds):
                centroids = sesh.run(self.centroids, feed_dict)
                feed_dict = {self.centroids_in: centroids}
                print "round {} -->  centroids: {}".format(i,centroids)
                if generate_all:
                    outfile = os.path.join(outdir, '{}_k{}_{}.jpg'.\
                                        format(basename,self.k,i))
                    self.generate_image(outfile=outfile)
            if not generate_all: # final image only
                outfile = os.path.join(outdir, '{}_k{}_{}.jpg'.\
                                    format(basename,self.k,i))
                self.generate_image(outfile=outfile)


    def _build_graph(self):
        """Construct tensorflow nodes for round of clustering"""
        pixels = tf.constant(self.arr, name="pixels", dtype=tf.float32)
        #self.centroids_in = tf.placeholder(name="centroids_in", dtype=tf.float32,
                                           #shape=(self.k,5))
        self.centroids_in = tf.Variable(np.array(random.sample(self.arr, self.k),
                                                 dtype=np.float32), name="centroids_in")
        # tiled should be shape(self.n_pixels,self.k,5)
        tiled_roids = tf.tile(tf.expand_dims(self.centroids_in,0),
                              multiples=[self.n_pixels,1,1], name="tiled_roids")
        tiled_pix = tf.tile(tf.expand_dims(pixels,1),
                            multiples=[1,self.k,1], name="tiled_pix")

        def radical_euclidean_dist(x,y):
            """Takes in 2 tensors and returns euclidean distance radical, i.e. dist**2"""
            return tf.square(tf.sub(x,y))

        # no need to take square root b/c positive reals and sqrt are isomorphic
        # should be shape(self.n_pixels, self.k)
        distances = tf.reduce_sum(radical_euclidean_dist(tiled_pix, tiled_roids),
                                  reduction_indices=2, name="distances")
        # should be shape(self.n_pixels)
        nearest = tf.to_int32(tf.argmin(distances,1), name="nearest")

        # should be list of len self.k with tensors of shape(size_cluster, 5)
        self.clusters = tf.dynamic_partition(pixels,nearest,self.k)
        # should be shape(self.k,5)
        self.centroids = tf.reshape(
            tf.concat(0,[tf.reduce_mean(cluster,0) for cluster in self.clusters]),
            shape=(self.k,5), name="centroids_out")


    def generate_image(self, outfile=None, save=True):
        new_arr = np.empty_like(self.pixels, dtype=np.uint8)
        centroids_rgb = np.int32(self.centroids.eval()[:,-3:])
        for centroid_rgb, cluster in itertools.izip(centroids_rgb,self.clusters):
            cluster_mn = np.int32(cluster.eval()[:,:2]/self.ratio)
            for pixel in cluster_mn:
                new_arr[tuple(pixel)] = centroid_rgb
        new_img = Image.fromarray(new_arr)
        new_img.show()
        if save and outfile:
            new_img.save(outfile, format='JPEG')



if __name__=="__main__":
    INFILE = '/Users/miriamshiffman/Downloads/536211-78101.jpg'
    OUTDIR = '/Users/miriamshiffman/Downloads/kmeanz'
    x = kmeans(INFILE, outdir=OUTDIR, k=10, rounds=5)