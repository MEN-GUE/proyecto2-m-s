import numpy as np

from src.optimizer.pso import pso, rastrigin


def sphere(x):
    return (x**2).sum(1)


def test_sphere_converges():
    _, best, _ = pso(sphere, -5 * np.ones(5), 5 * np.ones(5), n_particles=20, iters=300, patience=300, seed=1)
    assert best < 1e-4


def test_rastrigin_improves():
    _, best, hist = pso(rastrigin, -5.12 * np.ones(2), 5.12 * np.ones(2), n_particles=12, iters=100,
                        patience=100, seed=3)
    assert best < hist[0]["best"] and best < 2.0


def test_stops_when_stalled():
    _, _, hist = pso(lambda x: np.ones(len(x)), np.zeros(3), np.ones(3), iters=25, patience=5)
    assert len(hist) == 6
