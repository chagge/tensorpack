# -*- coding: UTF-8 -*-
# File: common.py
# Author: Yuxin Wu <ppwwyyxx@gmail.com>

import tensorflow as tf
from collections import namedtuple
from six.moves import zip

from tensorpack.models import ModelDesc
from ..tfutils import *

import multiprocessing

__all__ = ['PredictConfig', 'get_predict_func', 'PredictResult' ]

PredictResult = namedtuple('PredictResult', ['input', 'output'])

class PredictConfig(object):
    def __init__(self, **kwargs):
        """
        The config used by `get_predict_func`.

        :param session_init: a `utils.sessinit.SessionInit` instance to
            initialize variables of a session.
        :param input_data_mapping: Decide the mapping from each component in data
            to the input tensor, since you may not need all input variables
            of the Model to run the graph for prediction (for example
            the `label` input is not used if you only need probability distribution).

            It should be a list of int with length equal to `len(data_point)`,
            where each element in the list defines which input variables each
            component in the data point should be fed into.
            If not given, defaults to range(len(input_vars))

            For example, in image classification task, the testing
            dataset only provides datapoints of images (no labels). When
            the input variables of the model is: ::

                input_vars: [image_var, label_var]

            the mapping should then look like: ::

                input_data_mapping: [0] # the first component in a datapoint should map to `image_var`

        :param model: a `ModelDesc` instance
        :param output_var_names: a list of names of the output tensors to predict, the
            variables can be any computable tensor in the graph.
            Predict specific output might not require all input variables.
        :param return_input: whether to produce (input, output) pair or just output. default to False.
            It's only effective for `DatasetPredictorBase`.
        """
        def assert_type(v, tp):
            assert isinstance(v, tp), v.__class__
        # XXX does it work? start with minimal memory, but allow growth.
        # allow_growth doesn't seem to work very well in TF.
        self.session_config = kwargs.pop('session_config', get_default_sess_config(0.3))
        self.session_init = kwargs.pop('session_init', JustCurrentSession())
        assert_type(self.session_init, SessionInit)
        self.model = kwargs.pop('model')
        assert_type(self.model, ModelDesc)
        self.input_data_mapping = kwargs.pop('input_data_mapping', None)
        self.output_var_names = kwargs.pop('output_var_names')
        self.return_input = kwargs.pop('return_input', False)
        assert len(kwargs) == 0, 'Unknown arguments: {}'.format(str(kwargs.keys()))

def get_predict_func(config):
    """
    Produce a simple predictor function run inside a new session.
    :param config: a `PredictConfig` instance.
    :returns: A prediction function that takes a list of input values, and return
        a list of output values defined in ``config.output_var_names``.
    """
    output_var_names = config.output_var_names

    # input/output variables
    input_vars = config.model.get_input_vars()
    config.model._build_graph(input_vars, False)
    if config.input_data_mapping is None:
        input_map = input_vars
    else:
        input_map = [input_vars[k] for k in config.input_data_mapping if k >= 0]

    # check output_var_names against output_vars
    output_vars = get_vars_by_names(output_var_names)

    sess = tf.Session(config=config.session_config)
    config.session_init.init(sess)

    def run_input(dp):
        feed = dict(zip(input_map, dp))
        return sess.run(output_vars, feed_dict=feed)
    run_input.session = sess
    return run_input
