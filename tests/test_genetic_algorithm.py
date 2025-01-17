import numpy as np

from synnet.utils.ga_utils import crossover, fitness_sum, mutation


def test_crossover():
    np.random.seed(seed=137)
    num_parents = 10
    fp_size = 128
    offspring_size = 30
    population = np.ceil(np.random.random(size=(num_parents, fp_size)) * 2 - 1)

    offspring = crossover(parents=population, offspring_size=offspring_size)
    new_scores = np.array([fitness_sum(_) for _ in offspring])

    new_scores_ref = np.array(
        [
            69,
            72,
            65,
            62,
            79,
            70,
            70,
            60,
            62,
            71,
            61,
            79,
            65,
            63,
            73,
            66,
            66,
            64,
            69,
            71,
            74,
            67,
            64,
            64,
            67,
            66,
            56,
            58,
            69,
            69,
        ]
    )

    assert (new_scores == new_scores_ref).all()


def test_mutation():
    np.random.seed(seed=137)
    num_parents = 10
    fp_size = 128
    population = np.ceil(np.random.random(size=(num_parents, fp_size)) * 2 - 1)

    offspring = mutation(offspring_crossover=population, num_mut_per_ele=4, mut_probability=0.5)
    new_scores = np.array([fitness_sum(_) for _ in offspring])

    new_scores_ref = np.array(
        [
            70,
            64,
            62,
            60,
            68,
            66,
            65,
            59,
            68,
            77,
        ]
    )

    assert (new_scores == new_scores_ref).all()


def test_generation():
    np.random.seed(seed=137)
    num_parents = 10
    fp_size = 128
    offspring_size = 30
    ngen = 3
    population = np.ceil(np.random.random(size=(num_parents, fp_size)) * 2 - 1)

    scores = [fitness_sum(_) for _ in population]

    for _ in range(ngen):
        offspring = crossover(parents=population, offspring_size=offspring_size)
        offspring = mutation(offspring_crossover=offspring, num_mut_per_ele=4, mut_probability=0.5)
        new_population = np.concatenate([population, offspring], axis=0)
        new_scores = np.array(scores + [fitness_sum(_) for _ in offspring])
        scores = []

        for parent_idx in range(num_parents):
            max_score_idx = np.where(new_scores == np.max(new_scores))[0][0]
            scores.append(new_scores[max_score_idx])
            population[parent_idx, :] = new_population[max_score_idx, :]
            new_scores[max_score_idx] = -999999

    scores_ref = np.array([87.0, 86.0, 84.0, 84.0, 84.0, 82.0, 82.0, 82.0, 82.0, 82.0])

    new_scores_ref = np.array(
        [
            -9.99999e05,
            8.10000e01,
            8.10000e01,
            7.90000e01,
            7.90000e01,
            7.80000e01,
            7.70000e01,
            7.60000e01,
            7.60000e01,
            7.50000e01,
            7.00000e01,
            7.80000e01,
            7.30000e01,
            7.00000e01,
            8.10000e01,
            8.00000e01,
            -9.99999e05,
            7.80000e01,
            7.30000e01,
            -9.99999e05,
            7.40000e01,
            -9.99999e05,
            7.90000e01,
            7.60000e01,
            7.80000e01,
            7.90000e01,
            7.50000e01,
            7.90000e01,
            -9.99999e05,
            -9.99999e05,
            -9.99999e05,
            -9.99999e05,
            -9.99999e05,
            7.90000e01,
            7.30000e01,
            7.20000e01,
            7.60000e01,
            -9.99999e05,
            7.70000e01,
            8.00000e01,
        ]
    )

    assert (np.array(scores) == scores_ref).all()
    assert (new_scores == new_scores_ref).all()
