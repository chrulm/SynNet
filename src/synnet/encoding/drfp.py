"""Differential Fingerprints.
Source: https://github.com/reymond-group/drfp
Slightly modified.
"""
from collections import defaultdict
from hashlib import blake2b
from typing import Dict, Iterable, List, Set, Tuple, Union

import numpy as np
from rdkit.Chem import AllChem
from rdkit.Chem.rdchem import Mol


class NoReactionError(Exception):
    """Raised when the encoder attempts to encode a non-reaction SMILES.

    Attributes:
        message: a message containing the non-reaction SMILES
    """

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class DrfpEncoder:
    """A class for encoding SMILES as drfp fingerprints."""

    @staticmethod
    def shingling_from_mol(
        in_mol: Mol,
        radius: int = 3,
        rings: bool = True,
        min_radius: int = 0,
        get_atom_indices: bool = False,
    ) -> Union[List[str], Tuple[List[str], Dict[str, List[Set[int]]]]]:
        """Creates a molecular shingling from a RDKit molecule (rdkit.Chem.rdchem.Mol).

        Info:
            The shingling is created by extracting n-grams from the molecule in three steps:
                1. rings (optional)
                2. atoms (if min_radius == 0)
                3. fragments (if radius > min_radius)

        Arguments:
            in_mol: A RDKit molecule instance
            radius: The drfp radius (a radius of 3 corresponds to drfp6)
            rings: Whether or not to include rings in the shingling
            min_radius: The minimum radius that is used to extract n-grams
            get_atom_indices: Whether or not to return the atom indices that make up each n-gram

        Returns:
            The molecular shingling.
        """

        shingling = []
        atom_indices: Dict[str, List[Set[int]]] = defaultdict(list)
        #                   ^ ngram SMILES
        #                        ^ atom indices that make up this ngram

        if rings:
            for ring in AllChem.GetSymmSSSR(in_mol):
                bonds = set()
                ring = list(ring)
                indices = set()
                for i in ring:
                    for j in ring:
                        if i != j:
                            indices.add(i)
                            indices.add(j)
                            bond = in_mol.GetBondBetweenAtoms(i, j)
                            if bond is not None:
                                bonds.add(bond.GetIdx())

                ngram = AllChem.MolToSmiles(
                    AllChem.PathToSubmol(in_mol, list(bonds)),
                    canonical=True,
                    allHsExplicit=True,
                ).encode("utf-8")

                shingling.append(ngram)

                if get_atom_indices:
                    atom_indices[ngram].append(indices)

        # Add atoms
        if min_radius == 0:
            for i, atom in enumerate(in_mol.GetAtoms()):
                ngram = atom.GetSmarts().encode("utf-8")
                shingling.append(ngram)

                if get_atom_indices:
                    atom_indices[ngram].append(set([atom.GetIdx()]))

        # Add molecule fragments
        # https://rdkit.readthedocs.io/en/release_2019_03/GettingStartedInPython.html?highlight=pathtosubmol#explaining-bits-from-morgan-fingerprints
        for index, _ in enumerate(
            in_mol.GetAtoms()
        ):  # now get n-grams for each atom within a radius >= 1
            for i in range(1, radius + 1):
                p = AllChem.FindAtomEnvironmentOfRadiusN(
                    in_mol, i, index
                )  # (mol, radius, atom index)
                amap = {}  # : Dict[int, int] = {} # atom index,
                submol = AllChem.PathToSubmol(
                    in_mol, p, atomMap=amap
                )  # https://www.rdkit.org/docs/source/rdkit.Chem.rdmolops.html?highlight=pathtosubmol#rdkit.Chem.rdmolops.PathToSubmol

                if index not in amap:  # this atom is not within the radius of
                    continue

                smiles = AllChem.MolToSmiles(  # convert to ngram
                    submol,
                    rootedAtAtom=amap[index],
                    canonical=True,
                    allHsExplicit=True,
                )

                if smiles != "":
                    shingling.append(smiles.encode("utf-8"))
                    if get_atom_indices:
                        atom_indices[smiles.encode("utf-8")].append(set(amap.keys()))

        # Set ensures that the same shingle is not hashed multiple times
        # (which would not change the hash, since there would be no new minima)
        if get_atom_indices:
            return list(set(shingling)), atom_indices
        else:
            return list(set(shingling)), None

    @staticmethod
    def internal_encode(
        in_smiles: str,
        radius: int = 3,
        min_radius: int = 0,
        rings: bool = True,
        get_atom_indices: bool = False,
    ) -> Union[
        Tuple[np.ndarray, np.ndarray],
        Tuple[np.ndarray, np.ndarray, Dict[str, List[Dict[str, List[Set[int]]]]]],
        Union[None, Dict[str, List[Set[int]]]],
    ]:
        """Creates an drfp array from a reaction SMILES string.

        Arguments:
            in_smiles: A valid reaction SMILES string
            radius: The drfp radius (a radius of 3 corresponds to drfp6)
            min_radius: The minimum radius that is used to extract n-grams
            rings: Whether or not to include rings in the shingling

        Returns:
            A tuple with two arrays, the first containing the drfp hash values, the second the substructure SMILES
        """

        atom_indices = {}
        atom_indices["reactants"] = []
        atom_indices["products"] = []

        sides = in_smiles.split(">")
        if len(sides) < 3:
            raise NoReactionError(f"The following is not a valid reaction SMILES: '{in_smiles}'")

        if len(sides[1]) > 0:  # move reagents to reactants, i.e. A>B>C => A.B>C
            sides[0] += "." + sides[1]

        left = sides[0].split(".")  # reactants
        right = sides[2].split(".")  # products

        left_shingles = set()
        right_shingles = set()

        for l in left:
            mol = AllChem.MolFromSmiles(l)

            if not mol:  # probably an invalid SMILES
                atom_indices["reactants"].append(None)
                continue

            sh, ai = DrfpEncoder.shingling_from_mol(
                mol,
                radius=radius,
                rings=rings,
                min_radius=min_radius,
                get_atom_indices=True,
            )
            atom_indices["reactants"].append(ai)

            for s in sh:
                right_shingles.add(s)

        for r in right:
            mol = AllChem.MolFromSmiles(r)

            if not mol:
                atom_indices["products"].append(None)
                continue

            sh, ai = DrfpEncoder.shingling_from_mol(
                mol,
                radius=radius,
                rings=rings,
                min_radius=min_radius,
                get_atom_indices=True,
            )
            atom_indices["products"].append(ai)

            for s in sh:
                left_shingles.add(s)

        s = right_shingles.symmetric_difference(left_shingles)

        return DrfpEncoder.hash(list(s)), list(s), atom_indices

    @staticmethod
    def _hash(v: str) -> int:
        """Hashes a string to a 32-bit integer."""
        return int(blake2b(v, digest_size=4).hexdigest(), base=16)

    @staticmethod
    def hash(shingling: List[str]) -> np.ndarray:
        """Directly hash all the SMILES in a shingling to a 32-bit integerself.

        Arguments:
            shingling: A list of n-grams

        Returns:
            A list of hashed n-grams
        """
        return np.array([DrfpEncoder._hash(t) for t in shingling], dtype=np.int32)

    @staticmethod
    def fold(hash_values: np.ndarray, length: int = 2048) -> Tuple[np.ndarray, np.ndarray]:
        """Folds the hash values to a binary vector of a given length.

        Arguments:
            hash_value: An array containing the hash values
            length: The length of the folded fingerprint

        Returns:
            A tuple containing the folded fingerprint and the indices of the on bits
        """

        folded = np.zeros(length, dtype=np.uint8)
        on_bits = hash_values % length
        folded[on_bits] = 1

        return folded, on_bits

    @staticmethod
    def encode(
        X: Union[Iterable, str],
        n_folded_length: int = 2048,
        min_radius: int = 0,
        radius: int = 3,
        rings: bool = True,
        mapping: bool = False,
        atom_index_mapping: bool = False,
    ) -> Union[
        List[np.ndarray],
        Tuple[List[np.ndarray], Dict[int, Set[str]]],
        Tuple[List[np.ndarray], Dict[int, Set[str]]],
        List[Dict[str, List[Dict[str, List[Set[int]]]]]],
    ]:
        """Encodes a list of reaction SMILES using the drfp fingerprint.

        Args:
            X: An iterable (e.g. List) of reaction SMILES or a single reaction SMILES to be encoded
            n_folded_length: The folded length of the fingerprint (the parameter for the modulo hashing)
            min_radius: The minimum radius of a substructure (0 includes single atoms)
            radius: The maximum radius of a substructure
            rings: Whether to include full rings as substructures
            mapping: Return a feature to substructure mapping in addition to the fingerprints

        Returns:
            A list of drfp fingerprints or, if mapping is enabled, a tuple containing a list of drfp fingerprints and a mapping dict.
        """
        if isinstance(X, str):
            X = [X]

        if atom_index_mapping:
            mapping = True

        result = []
        result_map = defaultdict(set)
        atom_index_maps = []

        # Iterate over all reaction SMILES and
        #   - encode
        #   - fold into binary vector

        for _, x in enumerate(X):
            hashed_diff, smiles_diff, atom_index_map = DrfpEncoder.internal_encode(
                x,
                min_radius=min_radius,
                radius=radius,
                rings=rings,
                get_atom_indices=True,
            )

            difference_folded, on_bits = DrfpEncoder.fold(
                hashed_diff,
                length=n_folded_length,
            )

            if mapping:
                for unfolded_index, folded_index in enumerate(on_bits):
                    result_map[folded_index].add(smiles_diff[unfolded_index].decode("utf-8"))

            if atom_index_mapping:
                aidx_bit_map = {}
                aidx_bit_map["reactants"] = []
                aidx_bit_map["products"] = []

                for reactant in atom_index_map["reactants"]:
                    r = defaultdict(list)
                    for key, value in reactant.items():
                        if key in smiles_diff:
                            idx = smiles_diff.index(key)
                            r[on_bits[idx]].append(value)
                    aidx_bit_map["reactants"].append(r)

                for product in atom_index_map["products"]:
                    r = defaultdict(list)
                    for key, value in product.items():
                        if key in smiles_diff:
                            idx = smiles_diff.index(key)
                            r[on_bits[idx]].append(value)
                    aidx_bit_map["products"].append(r)

                atom_index_maps.append(aidx_bit_map)

            result.append(difference_folded)

        r = [result]

        if mapping:
            r.append(result_map)

        if atom_index_mapping:
            r.append(atom_index_maps)

        if len(r) == 1:
            return r[0]
        else:
            return tuple(r)
