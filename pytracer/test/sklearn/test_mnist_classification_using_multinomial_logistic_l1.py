# https://scikit-learn.org/stable/auto_examples/linear_model/plot_sparse_logistic_regression_mnist.html#sphx-glr-auto-examples-linear-model-plot-sparse-logistic-regression-mnist-py

import pytest
import time

import numpy as np
from sklearn.datasets import fetch_openml
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.utils import check_random_state


def mnist_classification_using_multinomial_logistic_l1():

    # Author: Arthur Mensch <arthur.mensch@m4x.org>
    # License: BSD 3 clause

    np.random.seed(42)

    # Turn down for faster convergence
    t0 = time.time()
    train_samples = 5000

    # Load data from https://www.openml.org/d/554
    X, y = fetch_openml('mnist_784', version=1, return_X_y=True)

    random_state = check_random_state(0)
    permutation = random_state.permutation(X.shape[0])
    X = X[permutation]
    y = y[permutation]
    X = X.reshape((X.shape[0], -1))

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, train_size=train_samples, test_size=10000)

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    # Turn up tolerance for faster convergence
    clf = LogisticRegression(
        C=50. / train_samples, penalty='l1', solver='saga', tol=0.1
    )
    clf.fit(X_train, y_train)
    sparsity = np.mean(clf.coef_ == 0) * 100
    score = clf.score(X_test, y_test)
    # print('Best C % .4f' % clf.C_)
    print("Sparsity with L1 penalty: %.2f%%" % sparsity)
    print("Test score with L1 penalty: %.4f" % score)

    coef = clf.coef_.copy()
    #plt.figure(figsize=(10, 5))
    scale = np.abs(coef).max()
    # for i in range(10):
    #     l1_plot = plt.subplot(2, 5, i + 1)
    #     l1_plot.imshow(coef[i].reshape(28, 28), interpolation='nearest',
    #                    cmap=plt.cm.RdBu, vmin=-scale, vmax=scale)
    #     l1_plot.set_xticks(())
    #     l1_plot.set_yticks(())
    #     l1_plot.set_xlabel('Class %i' % i)
    # plt.suptitle('Classification vector for...')

    run_time = time.time() - t0
    print('Example run in %.3f s' % run_time)
    # plt.show()


@pytest.mark.xfail
@pytest.mark.usefixtures("turn_numpy_ufunc_on", "cleandir")
def test_trace_only_ufunc_on(script_runner):
    ret = script_runner.run("pytracer", "trace",
                            f"--module {__file__}")
    assert ret.success


@pytest.mark.usefixtures("turn_numpy_ufunc_off", "cleandir")
def test_trace_only_ufunc_off(script_runner):
    ret = script_runner.run("pytracer", "trace",
                            f"--module {__file__}")
    assert ret.success


@pytest.mark.xfail
@pytest.mark.usefixtures("turn_numpy_ufunc_off", "cleandir", "parse")
def test_trace_parse(nsamples, script_runner):
    for _ in range(nsamples):
        ret = script_runner.run("pytracer", "trace",
                                f"--module {__file__}")
        assert ret.success


if __name__ == "__main__":
    mnist_classification_using_multinomial_logistic_l1()
    print("End")
