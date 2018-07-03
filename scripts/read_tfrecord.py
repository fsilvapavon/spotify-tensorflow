#!/usr/bin/env python
"""
Usage

read_tfrecord.py [--schema path_to_schema] path_to_tfrecord1 ... path_to_tfrecordN | less

0. clean up JSON output to be jq friendly [DONE]
0.5 support sparse features
1. clean this up, remove .py, rename it [in progress]
2. put this in /bin, update setup.py

"""

import argparse
import tensorflow as tf
from tensorflow.core.example import example_pb2
from tensorflow.python.lib.io import file_io
from tensorflow_metadata.proto.v0.schema_pb2 import Schema
from tensorflow_metadata.proto.v0.schema_pb2 import INT, FLOAT, BYTES
from tensorflow_transform.coders import example_proto_coder
from tensorflow_transform.tf_metadata import dataset_schema
import json
import numpy as np
from google.protobuf.json_format import MessageToJson


def get_args():
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--schema', '-s', help="Path to Schema protobuf file. Uses Example if not "
                                               "supplied.")
    parser.add_argument('tfrecord_paths', metavar='TFRECORD_PATH', nargs='+', help="TFRecord files")
    return parser.parse_args()


to_tf_type = {INT: tf.int32,
              FLOAT: tf.float32,
              BYTES: tf.string}

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)

def feature_to_feature_spec(feature):
    # for PoC cover only fixed/var len features
    # TODO support sparse features
    if len(feature.shape.dim) != 0:
        return feature.name, tf.FixedLenFeature(shape=tuple(d.size for d in feature.shape.dim),
                                                dtype=to_tf_type[feature.type])
    else:
        return feature.name, tf.VarLenFeature(dtype=to_tf_type[feature.type])

def schema_proto_to_feature_spec(schema_file):
    schema = Schema()
    with file_io.FileIO(schema_file, "r") as f:
        schema.ParseFromString(f.read())

    name_to_feature = dict(map(feature_to_feature_spec, schema.feature))
    return name_to_feature.copy()


if __name__ == '__main__':
    cmdline_args = get_args()

    if cmdline_args.schema:
        schema = dataset_schema.from_feature_spec(schema_proto_to_feature_spec(cmdline_args.schema))
        coder = example_proto_coder.ExampleProtoCoder(schema)

        for tfrecord_file in cmdline_args.tfrecord_paths:
            for i in tf.python_io.tf_record_iterator(tfrecord_file):
                decoded = coder.decode(i)
                decoded_json = json.dumps(decoded, cls=NumpyEncoder)
                print(decoded_json)
    else:
        for tfrecord_file in cmdline_args.tfrecord_paths:
            for i in tf.python_io.tf_record_iterator(tfrecord_file):
                e = example_pb2.Example()
                e.ParseFromString(i)
                print(MessageToJson(e))
