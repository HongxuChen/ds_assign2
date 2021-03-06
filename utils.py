#!/usr/bin/env python
from __future__ import print_function

import operator
import os

import numpy as np

import config
# noinspection PyPep8Naming
from gf import GF
from log_helper import init_logger, get_logger


class RAIDCheckError(Exception):
    """
    used for general RAID check error
    """

    def __init__(self, msg):
        super(RAIDCheckError, self).__init__(msg)


# noinspection PyPep8Naming
def setup_disks(root_path, N):
    """
    "initialize" RAID disks
    :param root_path: "disk location"
    :param N: number of total disks
    :return:
    """
    if not os.path.isdir(root_path):
        os.mkdir(root_path)
    for i in xrange(N):
        fname = config.disk_prefix + str(i)
        fpath = os.path.join(root_path, fname)
        if not os.path.isdir(fpath):
            os.mkdir(fpath)


def read_content(fpath):
    """lowest read"""
    with open(fpath, 'rb') as fh:
        return fh.read()


def write_content(fpath, content):
    """lowest write"""
    with open(fpath, 'wb') as fh:
        fh.write(content)


# noinspection PyMethodMayBeStatic
def gf_1darray_add(A1, A2):
    """
    add operation for 2 same shaped ndarray
    :param A1:
    :param A2:
    :return: 1darray
    """
    return (A1 ^ A2).ravel(1)


def gf_a_multiply_list(a, l):
    """
    multiplication of a and l
    :param a: scala type
    :param l:
    :return: list of int
    """
    gf = GF()
    return [gf.multiply(int(i), a) for i in l]


def gen_p(data_ndarray, ndim):
    """
    generate res from data_ndarray with XOR
    :param ndim: ndarray dimension
    :param data_ndarray: the data array
    :return: the parity of the data_ndarray
    """
    assert ndim in [1, 2]
    res = np.bitwise_xor.reduce(data_ndarray)
    assert res.ndim == 1
    if ndim == 1:
        return res
    # ndim == 2
    new_num = res.shape[0]
    res.shape = (1, new_num)
    return res


def gen_q(data_ndarray, ndim):
    """
    generate q using GF^8
    :param data_ndarray: the data ndarray
    :param ndim: real dim
    :return: q_ndarray with shape=(1, byte_ndarray.shape[1])
    """
    transposed = np.transpose(data_ndarray)
    # print(data_ndarray.shape)
    get_logger().info('transposed\n{}'.format(transposed))
    gf = GF()
    q_list = []
    for _1darray in transposed:
        bv_list = []
        for i, arr_val in enumerate(_1darray):
            res_i = gf.multiply(gf.generator[i % gf.circle], int(arr_val))
            # print('i={}, arr_val={}, res_i={}'.format(i, arr_val, res_i))
            bv_list.append(res_i)
            # map(lambda i: print(i), bv_list)
        q_value = reduce(operator.xor, bv_list)
        q_list.append(q_value)
    arr = np.array(q_list, ndmin=ndim, dtype=config.BYTE_TYPE)
    get_logger().info("arr={}".format(arr))
    # assert arr.shape[1] == data_ndarray.shape[1]
    return arr


def check_data_p(byte_ndarray):
    """check p integrity, byte_ndarray is whole data ndarray; so XOR should be all zeros"""
    computed = gen_p(byte_ndarray, ndim=1)
    if np.count_nonzero(computed) != 0:
        msg = 'xor of arrays not all zeros, computed={}'.format(computed)
        raise RAIDCheckError(msg)


def check_q(data_ndarray, q_ndarray):
    """
    check data_ndarray against q_ndarray
    :param data_ndarray:
    :param q_ndarray:
    :return:
    """
    computed = gen_q(data_ndarray, ndim=2)
    if not np.array_equal(computed, q_ndarray):
        msg = 'Q check failed, q_ndarray={}, computed={}'.format(q_ndarray, computed)
        raise RAIDCheckError(msg)


def simple_test(raid_level, test_recovery=True):
    """a simple test function"""
    init_logger()
    raid = raid_level(4)
    data_fname = 'good.dat'
    original_content = 'good_morning_sir'
    # original_content = b'\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11\x12\x13'
    size = len(original_content)
    raid.write(original_content, data_fname)
    raid_content = raid.read(data_fname, size)
    print(raid_content.__repr__())
    assert raid_content == original_content
    if test_recovery:
        error_index = 2
        raid.recover(data_fname, error_index)
