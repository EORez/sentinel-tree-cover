import numpy as np
import tensorflow as tf
from tflearn.layers.conv import global_avg_pool
import itertools
from tensorflow.python.keras.layers import Conv2D, Lambda, Dense, Multiply, Add

def ndvi(x, verbose = False):
    # (B8 - B4)/(B8 + B4)
    NIR = x[:, :, :, 3]
    RED = x[:, :, :, 2]
    ndvis = (NIR-RED) / (NIR+RED)
    if verbose:
        mins = np.min(ndvis)
        maxs = np.max(ndvis)
        if mins < -1 or maxs > 1:
            print("ndvis error: {}, {}".format(mins, maxs))
    x = np.concatenate([x, ndvis[:, :, :, np.newaxis]], axis = -1)
    return x

def evi(x, verbose = False):
    # 2.5 x (08 - 04) / (08 + 6 * 04 - 7.5 * 02 + 1)
    NIR = x[:, :, :, 3]
    RED = x[:, :, :, 2]
    BLUE = x[:, :, :, 0]
    evis = 2.5 * ( (NIR-RED) / (NIR + (6*RED) - (7.5*BLUE) + 1))
    evis = np.clip(evis, -1.5, 1.5)
    x = np.concatenate([x, evis[:, :, :, np.newaxis]], axis = -1)
    return x
    
def savi(x, verbose = False):
    # (1.5) * ((08 - 04)/ (08 + 04 + 0.5))
    NIR = x[:, :, :, 3]
    RED = x[:, :, :, 2]
    savis = 1.5 * ( (NIR-RED) / (NIR+RED +0.5))
    if verbose:
        mins = np.min(savis)
        maxs = np.max(savis)
        if mins < -1.0 or maxs > 1.0:
        	print("SAVI: {} {}".format(mins, maxs))
    x = np.concatenate([x, savis[:, :, :, np.newaxis]], axis = -1)
    return x

def msavi2(x, verbose = False):
    # (2 * NIR + 1 - sqrt((2*NIR + 1)^2 - 8*(NIR-RED)) / 2
    NIR = x[:, :, :, 3]
    RED = x[:, :, :, 2]
    for i in range(x.shape[0]):
        NIR_i = x[i, :, :, 3]
        RED_i = x[i, :, :, 2]
        under_sqrt = (2*NIR_i+1)**2 - 8*(NIR_i-RED_i)
        under_sqrt = np.min(under_sqrt)
        if under_sqrt <= 0:
            print("MSAVI2 negative sqrt at: {}, {}".format(i, under_sqrt))
    msavis = (2 * NIR + 1 - np.sqrt( (2*NIR+1)**2 - 8*(NIR-RED) )) / 2
    if verbose:
        mins = np.min(msavis)
        maxs = np.max(msavis)
        if mins < -1 or maxs > 1:
            print("MSAVIS error: {}, {}".format(mins, maxs))
    x = np.concatenate([x, msavis[:, :, :, np.newaxis]], axis = -1)
    return x

def bi(x, verbose = False):
    # (2 + 0 - 1) / (2 + 0 + 1)
    BLUE = x[:, :, :, 0]
    RED = x[:, :, :, 2]
    GREEN = x[:, :, :, 1]
    bis = (BLUE + RED - GREEN) / (BLUE + RED + GREEN)
    if verbose:
        mins = np.min(bis)
        maxs = np.max(bis)
        if mins < -1.5 or maxs > 1.5:
            print("bis error: {}, {}".format(mins, maxs))
    x = np.concatenate([x, bis[:, :, :, np.newaxis]], axis = -1)
    return x

def si(x, verbose = False):
    # (1 - B2) * (1 - B3) * (1 - B4) ** 1/3
    BLUE = x[:, :, :, 0]
    RED = x[:, :, :, 2]
    GREEN = x[:, :, :, 1]
    sis = np.power( (1-BLUE) * (1 - GREEN) * (1 - RED), 1/3)
    if verbose:
        mins = np.min(sis)
        maxs = np.max(sis)
        if mins < -1 or maxs > 1:
            print("sis error: {}, {}".format(mins, maxs))
    x = np.concatenate([x, sis[:, :, :, np.newaxis]], axis = -1)
    return x

def ndmi(x):
    ndmis = [(im[:, :, 5] - im[:, :, 9]) / (im[:, :, 5] + im[:, :, 9]) for im in x]
    ndmis = np.stack(ndmis)
    x = np.concatenate([x, ndmis[:, :, :, np.newaxis]], axis = -1)
    return x

def Fully_connected(x, units, layer_name='fully_connected') :
    with tf.name_scope(layer_name) :
        return tf.layers.dense(inputs=x, use_bias=True, units=units)

def Relu(x):
    return tf.nn.relu(x)

def Sigmoid(x):
    return tf.nn.sigmoid(x)

def Global_Average_Pooling(x):
    return global_avg_pool(x, name='Global_avg_pooling')

def Squeeze_excitation_layer(input_x, out_dim, ratio, layer_name):
    with tf.name_scope(layer_name) :
        squeeze = global_avg_pool(input_x)

        excitation = Fully_connected(squeeze, units=out_dim / ratio, layer_name=layer_name+'_fully_connected1')
        excitation = Relu(excitation)
        excitation = Fully_connected(excitation, units=out_dim, layer_name=layer_name+'_fully_connected2')
        excitation = Sigmoid(excitation)

        excitation = tf.reshape(excitation, [-1,1,1,out_dim])

        scale = input_x * excitation

        return scale
    
def convGRU(x, cell_fw, cell_bw, ln):
        output, final = tf.nn.bidirectional_dynamic_rnn(
            cell_fw, cell_bw, x, ln, dtype=tf.float32)
        #output = tf.concat(output, -1)
        #final = tf.concat(final, -1)
        return output, final