##############################################################################
# Copyright 2017-2018 Rigetti Computing
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
##############################################################################

import matplotlib
matplotlib.use('Agg')

import pytest
import numpy as np
from mock import Mock, patch
from matplotlib.pyplot import figure

import qutip as qt
from mpl_toolkits.mplot3d import Axes3D

from pyquil.gates import X
from pyquil.quil import Program

import grove.tomography.utils as ut
import grove.tomography.operator_utils as o_ut

from grove.tomography.operator_utils import FROBENIUS


def test_sample_outcomes_make_histogram():
    n = 10
    N = 10000

    np.random.seed(2342)
    probs = np.random.rand(n)
    probs /= probs.sum()

    histogram = ut.make_histogram(ut.sample_outcomes(probs, N), n) / float(N)
    assert np.allclose(histogram, probs, atol=.01)


def test_basis_state_preps():
    II, IX, XI, XX = ut.basis_state_preps(0, 1)
    assert II.out() == "I 0\nI 1\n"
    assert IX.out() == "I 0\nX 1\n"
    assert XI.out() == "X 0\nI 1\n"
    assert XX.out() == "X 0\nX 1\n"


def test_sample_bad_readout():
    np.random.seed(234)
    assignment_probs = .3*np.random.rand(4, 4) + np.eye(4)
    assignment_probs /= assignment_probs.sum(axis=0)[np.newaxis, :]
    cxn = Mock()
    cxn.wavefunction.return_value.amplitudes = 0.5j * np.ones(4)
    with patch("grove.tomography.utils.sample_outcomes") as so:
        ut.sample_bad_readout(Program(X(0), X(1), X(0), X(1)), 10000, assignment_probs, cxn)
        assert np.allclose(so.call_args[0][0], 0.25 * assignment_probs.sum(axis=1))


def test_estimate_assignment_probs():
    np.random.seed(2345)
    outcomes = np.random.randint(0, 1000, size=(4, 4))
    aprobs = ut.estimate_assignment_probs(outcomes)
    assert np.allclose(aprobs.T * outcomes.sum(axis=1)[:, np.newaxis], outcomes)


def test_product_basis():
    X, Y, Z, I = ut.QX, ut.QY, ut.QZ, ut.QI

    assert o_ut.is_hermitian(X.data.toarray())

    labels = ["II", "IX", "IY", "IZ", "XI", "XX", "XY", "XZ",
              "YI", "YX", "YY", "YZ", "ZI", "ZX", "ZY", "ZZ"]
    d = {"I": I / np.sqrt(2), "X": X / np.sqrt(2), "Y": Y / np.sqrt(2), "Z": Z / np.sqrt(2)}
    ops = [qt.tensor(d[s[0]], d[s[1]]) for s in labels]

    for ((ll1, op1), ll2, op2) in zip(ut.PAULI_BASIS.product(ut.PAULI_BASIS), labels, ops):
        assert ll1 == ll2
        assert (op1 - op2).norm(FROBENIUS) < o_ut.EPS


def test_states():
    preparations = ut.QX, ut.QY, ut.QZ
    states = ut.generated_states(ut.GS, preparations)
    assert (states[0] - ut.ES).norm(FROBENIUS) < o_ut.EPS
    assert (states[1] - ut.ES).norm(FROBENIUS) < o_ut.EPS
    assert (states[2] - ut.GS).norm(FROBENIUS) < o_ut.EPS
    assert (ut.n_qubit_ground_state(2) - qt.tensor(ut.GS, ut.GS)).norm(FROBENIUS) < o_ut.EPS




def test_povm():
    pi_basis = ut.POVM_PI_BASIS
    confusion_rate_matrix = np.eye(2)
    povm = o_ut.make_diagonal_povm(pi_basis, confusion_rate_matrix)

    assert (povm.ops[0] - pi_basis.ops[0]).norm(FROBENIUS) < o_ut.EPS
    assert (povm.ops[1] - pi_basis.ops[1]).norm(FROBENIUS) < o_ut.EPS

    with pytest.raises(o_ut.CRMUnnormalizedError):
        confusion_rate_matrix = np.array([[.8, 0.],
                                     [.3, 1.]])
        _ = o_ut.make_diagonal_povm(pi_basis, confusion_rate_matrix)

    with pytest.raises(o_ut.CRMValueError):
        confusion_rate_matrix = np.array([[.8, -.1],
                                     [.2, 1.1]])
        _ = o_ut.make_diagonal_povm(pi_basis, confusion_rate_matrix)


def test_basis_labels():
    for num_qubits, desired_labels in [(1, ['0', '1']),
                                       (2, ['00', '01', '10', '11'])]:
        generated_labels = ut.basis_labels(num_qubits)
        assert desired_labels == generated_labels


def test_visualization():
    ax = Axes3D(figure())
    # Without axis.
    ut.state_histogram(ut.GS, title="test")
    # With axis.
    ut.state_histogram(ut.GS, ax, "test")
    assert ax.get_title() == "test"

    ptX = ut.PAULI_BASIS.transfer_matrix(qt.to_super(ut.QX)).toarray()
    ax = Mock()
    with patch("matplotlib.pyplot.colorbar"):
        ut.plot_pauli_transfer_matrix(ptX, ax, ut.PAULI_BASIS.labels, "bla")
    assert ax.imshow.called
    assert ax.set_xlabel.called
    assert ax.set_ylabel.called