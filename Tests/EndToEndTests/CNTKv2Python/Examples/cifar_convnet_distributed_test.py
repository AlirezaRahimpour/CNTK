﻿# Copyright (c) Microsoft. All rights reserved.

# Licensed under the MIT license. See LICENSE.md file in the project root
# for full license information.
# ==============================================================================

import numpy as np
import os
import sys
import signal
import subprocess
import re
import pytest
from cntk.ops.tests.ops_test_utils import cntk_device
from cntk.cntk_py import DeviceKind_GPU
from cntk.device import set_default_device

abs_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(abs_path)

script_under_test = os.path.join(abs_path, "..", "..", "..", "..", "Examples", "Image", "Classification", "ConvNet", "Python", "ConvNet_CIFAR10_DataAug_Distributed.py")

TOLERANCE_ABSOLUTE = 2E-1
TIMEOUT_SECONDS = 300

def mpiexec_test(device_id, script, params, expected_test_error, allow_tolerance, mb_should_match):
    if cntk_device(device_id).type() != DeviceKind_GPU:
       pytest.skip('test only runs on GPU')

    cmd = ["mpiexec", "-n", "2", "python", script] + params
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    if sys.version_info[0] < 3:
        out = p.communicate()[0]
    else:
        try:
            out = p.communicate(timeout=TIMEOUT_SECONDS)[0]  # in case we have a hang
        except subprocess.TimeoutExpired:
            os.kill(p.pid, signal.CTRL_C_EVENT)
            raise RuntimeError('Timeout in mpiexec, possibly hang')
    str_out = out.decode(sys.getdefaultencoding())
    results = re.findall("Final Results: Minibatch\[.+?\]: errs = (.+?)%", str_out)
    assert len(results) == 2

    if mb_should_match:
        assert results[0] == results[1]
    else:
        assert np.allclose(float(results[0])/100, float(results[1])/100,
                           atol=TOLERANCE_ABSOLUTE)

    assert np.allclose(float(results[0])/100, expected_test_error,
                       atol=TOLERANCE_ABSOLUTE)

def test_cifar_convnet_distributed_mpiexec(device_id):
    params = [ "-e", "2"] # 2 epochs with simple aggregator
    mpiexec_test(device_id, script_under_test, params, 0.617, False, True)

def test_cifar_convnet_distributed_1bitsgd_mpiexec(device_id):
    params = ["-q", "1", "-e", "2"] # 2 epochs with 1BitSGD
    mpiexec_test(device_id, script_under_test, params, 0.617, False, True)


def test_cifar_convnet_distributed_blockmomentum_mpiexec(device_id):
    params = ["-b", "32000", "-e", "2"] # 2 epochs with block momentum
    piexec_test(device_id, script_under_test, params, 0.6457, True, False)
