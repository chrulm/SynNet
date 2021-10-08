# SynNet
This repo contains the code and analysis scripts for our amortized approach to synthetic tree generation using neural networks. Our model can serve as both a synthesis planning tool and as a tool for synthesizable molecular design.

The method is described in detail in the publication "Amortized tree generation for bottom-up synthesis planning and synthesizable molecular design" [TODO add link to arXiv after publication] and summarized below.

## Summary
### Overview
We model synthetic pathways as tree structures called *synthetic trees*. A valid synthetic tree has one root node (the final product molecule) linked to purchasable building blocks (encoded as SMILES strings) via feasible reactions according to a list of discrete reaction templates (examples of templates encoded as SMARTS strings in [data/rxn_set_hb.txt](./data/rxn_set_hb.txt)). At a high level, each synthetic tree is constructed one reaction step at a time in a bottom-up manner, starting from purchasable building blocks.

The model consists of four modules, each containing a multi-layer perceptron (MLP): 

1. An *Action Type* selection function that classifies action types among the four possible actions (“Add”, “Expand”, “Merge”, and “End”) in building the synthetic tree.
2. A *First Reactant* selection function that predicts an embedding for the first reactant. A candidate molecule is identified for the first reactant through a k-nearest neighbors (k-NN) search from the list of potential building blocks.
3. A *Reaction* selection function whose output is a probability distribution over available reaction templates, from which inapplicable reactions are masked (based on reactant 1) and a suitable template is then sampled using a greedy search.
4. A *Second Reactant* selection function that identifies the second reactant if the sampled template is bi-molecular. The model predicts an embedding for the second reactant, and a candidate is then sampled via a k-NN search from the masked set of building blocks.

These four modules predict the probability distributions of actions to be taken within a single reaction step, and determine the nodes to be added to the synthetic tree under construction. All of these networks are conditioned on the target molecule embedding.

### Synthesis planning
This task is to infer the synthetic pathway to a given target molecule. We formulate this problem as generating a synthetic tree such that the product molecule it produces (i.e., the molecule at the root node) matches the desired target molecule.

For this task, we can take a molecular embedding for the desired product, and use it as input to our model to produce a synthetic tree. If the desired product is successfully recovered, then the final root molecule will match the desired molecule used to create the input embedding. If the desired product is not successully recovered, it is possible the final root molecule may still be *similar* to the desired molecule used to create the input embedding, and thus our tool can also be used for *synthesizable analog recommendation*.
### Synthesizable molecular design
This task is to optimize a molecular structure with respect to an oracle function (e.g. bioactivity), while ensuring the synthetic accessibility of the molecules. We formulate this problem as optimizing the structure of a synthetic tree with respect to the desired properties of the product molecule it produces.

To do this, we optimize the molecular embedding of the molecule using a genetic algorithm and the desired oracle function. The optimized molecule embedding can then be used as input to our model to produce a synthetic tree, where the final root molecule corresponds to the optimized molecule.

## Setup instructions

### Setting up the environment
You can use conda to create an environment containing the necessary packages and dependencies for running synth_net by using the provided YAML file:

```
conda env create -f env/synthenv.yml
```

If you update the environment and would like to save the updated environment as a new YAML file using conda, use:

```
conda env export > path/to/env.yml
```

### Unit tests
To check that everything has been set-up correctly, you can run the unit tests from within the [tests/](./tests/) directory by typing:

```
python -m unittest
```

You should get no errors if everything ran correctly.

## Code Structure
The code is structured as follows:

```
synth_net/
├── data
│   └── rxn_set_hb.txt
├── environment.yml
├── LICENSE
├── README.md
├── scripts
│   ├── compute_embedding_mp.py
│   ├── compute_embedding.py
│   ├── generation_fp.py
│   ├── generation.py
│   ├── gin_supervised_contextpred_pre_trained.pth
│   ├── _mp_decode.py
│   ├── _mp_predict_beam.py
│   ├── _mp_predict_multireactant.py
│   ├── _mp_predict.py
│   ├── _mp_search_similar.py
│   ├── _mp_sum.py
│   ├── mrr.py
│   ├── optimize_ga.py
│   ├── predict-beam-fullTree.py
│   ├── predict_beam_mp.py
│   ├── predict-beam-reactantOnly.py
│   ├── predict_mp.py
│   ├── predict_multireactant_mp.py
│   ├── predict.py
│   ├── read_st_data.py
│   ├── sample_from_original.py
│   ├── search_similar.py
│   ├── sketch-synthetic-trees.py
│   ├── st2steps.py
│   ├── st_split.py
│   └── temp.py
├── setup.py
├── synth_net
│   ├── data_generation
│   │   ├── check_all_template.py
│   │   ├── filter_unmatch.py
│   │   ├── __init__.py
│   │   ├── make_dataset_mp.py
│   │   ├── make_dataset.py
│   │   ├── _mp_make.py
│   │   ├── _mp_process.py
│   │   └── process_rxn_mp.py
│   ├── __init__.py
│   ├── models
│   │   ├── act.py
│   │   ├── mlp.py
│   │   ├── prepare_data.py
│   │   ├── rt1.py
│   │   ├── rt2.py
│   │   └── rxn.py
│   └── utils
│       ├── data_utils.py
│       ├── ga_utils.py
│       └── __init__.py
└── tests
    ├── create-unittest-data.py
    └── test_DataPreparation.py
```

The model implementations can be found in [synth_net/models/](synth_net/models/), with processing and analysis scripts located in [scripts/](./scripts/). 

## Instructions
Before running anything, you need to add the root directory to the Python path. One option for doing this is to run the following command in the root `SynNet` directory:

```
export PYTHONPATH=`pwd`:$PYTHONPATH
```

### Overview
Before training any models, you will first need to preprocess the set of reaction templates which you would like to use. You can use either a new set of reaction templates, or the provided Hartenfeller-Button (HB) set of reaction templates (see [data/rxn_set_hb.txt](data/rxn_set_hb.txt)). To preprocess a new dataset, you will need to:
1. Preprocess the data to identify applicable reactants for each reaction template
2. Generate the synthetic trees by random selection
3. Split the synthetic trees into training, testing, and validation splits
4. Featurize the nodes in the synthetic trees using molecular fingerprints
5. Prepare the training data for each of the four networks

Once you have preprocessed a training set, you can begin to train a model by training each of the four networks separately (the *Action*, *First Reactant*, *Reaction*, and *Second Reactant* networks).

After training a new model, you can then use the trained model to make predictions and construct synthetic trees for a list given set of molecules.

You can also perform molecular optimization using a genetic algorithm.

Instructions for all of the aforementioned steps are described in detail below.

In addition to the aforementioned types of jobs, we have also provide below instructions for (1) sketching synthetic trees and (2) calculating the mean reciprocal rank of reactant 1.

### Processing the data: reaction templates and applicable reactants

Given a set of reaction templates and a list of buyable building blocks, we first need to assign applicable reactants for each template. Under [synth_net/synth_net/data_generation/](./synth_net/synth_net/data_generation/), run:

```
python process_rxn_mp.py
```

This will save the reaction templates and their corresponding building blocks in a JSON file. Then, run:

```
python filter_unmatch.py 
```

This will filter out buyable building blocks which didn't match a single template.

### Generating the synthetic path data by random selection
Under [synth_net/synth_net/data_generation/](./synth_net/synth_net/data_generation/), run:

```
python make_dataset_mp.py
```

This will generate synthetic path data saved in a JSON file. Then, to make the dataset more pharmaceutically revelant, we can change to [synth_net/scripts/](./synth_net/scripts/) and run:

```
python sample_from_original.py 
```

This will filter out the samples where the root node QED is less than 0.5, or randomly with a probability less than 1 - QED/0.5.

### Splitting data into training, validation, and testing sets, and removing duplicates
Under [synth_net/scripts/](./synth_net/scripts/), run:

```
python st_split.py
```

The default split ratio is 6:2:2 for training, validation, and testing sets.

### Featurizing data
Under [synth_net/scripts/](./synth_net/scripts/), run:

```
python st2steps.py -r 2 -b 4096 -d train
```

This will featurize the synthetic tree data into step-by-step data which can be used for training. The flag *-r* indicates the fingerprint radius, *-b* indicates the number of bits to use for the fingerprints, and *-d* indicates which dataset split to featurize. 

### Preparing training data for each network
Under [synth_net/synth_net/models/](./synth_net/synth_net/models/), run:

```
python prepare_data.py --radius 2 --nbits 4096
```

This will prepare the training data for the networks.

Each is a training script and can be used as follows (using the action network as an example):

```
python act.py --radius 2 --nbits 4096
```

This will train the network and save the model parameters at the state with the best validation loss in a logging directory, e.g., **`act_hb_fp_2_4096_logs`**. One can use tensorboard to monitor the training and validation loss.

### Reconstructing a list of molecules
To test how good the trained model is at reconstructing from a set of known molecules, we can evaluate the model for the task of single-shot retrosynthesis.

[TODO add checkpoints to prediction scripts // save trees periodically. otherwise just saves at end and is problematic of job times out]
```
python predict.py --radius 2 --nbits 4096
``` 

This script will feed a list of molecules from the test data and save the decoded results (predicted synthesis trees) to [synth_net/results/](./synth_net/results/).

Note: this file reads parameters from a directory with a name such as **`hb_fp_vx`**, where "hb" indicates the Hartenfeller-Button dataset, "fp" indicates to use the fingerprint featurization (as opposed to GIN embeddings), and "vx" indicates the version (x in this case).
### Molecular optimization
Under [synth_net/scripts/](./synth_net/scripts/), run:

```
python optimization_ga.py
```

This script uses a genetic algorithm to optimize molecular embeddings and returns the predicted synthetic trees for the optimized molecular embedding.

### Sketching synthetic trees
To visualize the synthetic trees, run:

```
python scripts/sketch-synthetic-trees.py --file /pool001/whgao/data/synth_net/st_hb/st_train.json.gz --saveto ./ --nsketches 5 --actions 3
```

This will sketch 5 synthetic trees with 3 or more actions to the current ("./") directory (you can play around with these variables or just also leave them out to use the defaults).

### Testing the mean reciprocal rank (MRR) of reactant 1
Under [synth_net/scripts/](./synth_net/scripts/), run:

```
python mrr.py --distance cosine
```