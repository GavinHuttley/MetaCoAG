#!/usr/bin/env python3

import numpy as np
import itertools
import os
import logging

from Bio import SeqIO
from multiprocessing import Pool


# Create logger
logger = logging.getLogger('MetaCoaAG 1.0')

# Set complements of each nucleotide
complements = {'A': 'T', 'C': 'G', 'G': 'C', 'T': 'A'}

# Set bits for each nucleotide
nt_bits = {'A': 0, 'C': 1, 'G': 2, 'T': 3}

VERY_SMALL_VAL = 0.0000001


def get_rc(seq):
    rev = reversed(seq)
    return "".join([complements.get(i, i) for i in rev])


def mer2bits(kmer):
    bit_mer = nt_bits[kmer[0]]
    for c in kmer[1:]:
        bit_mer = (bit_mer << 2) | nt_bits[c]
    return bit_mer


def compute_kmer_inds(k):
    kmer_inds = {}
    kmer_count_len = 0

    alphabet = 'ACGT'

    all_kmers = [''.join(kmer)
                 for kmer in itertools.product(alphabet, repeat=k)]
    all_kmers.sort()
    ind = 0
    for kmer in all_kmers:
        bit_mer = mer2bits(kmer)
        rc_bit_mer = mer2bits(get_rc(kmer))
        if rc_bit_mer in kmer_inds:
            kmer_inds[bit_mer] = kmer_inds[rc_bit_mer]
        else:
            kmer_inds[bit_mer] = ind
            kmer_count_len += 1
            ind += 1

    return kmer_inds, kmer_count_len


def count_kmers(args):
    seq, k, kmer_inds, kmer_count_len = args
    profile = np.zeros(kmer_count_len)
    arrs = []
    seq = list(seq.strip())

    for i in range(0, len(seq) - k + 1):
        bit_mer = mer2bits(seq[i:(i + k)])
        index = kmer_inds[bit_mer]
        profile[index] += 1

    return profile, profile/max(1, sum(profile))


def get_tetramer_profiles(output_path, sequences, nthreads):

    tetramer_profiles = {}
    normalized_tetramer_profiles = {}

    if os.path.isfile(output_path + "contig_tetramers.txt") and os.path.isfile(output_path + "normalized_contig_tetramers.txt"):
        i = 0
        with open(output_path + "contig_tetramers.txt") as tetramers_file:
            for line in tetramers_file.readlines():
                f_list = np.array([float(i)
                                   for i in line.split(" ") if i.strip()])
                tetramer_profiles[i] = f_list
                i += 1

        i = 0
        with open(output_path + "normalized_contig_tetramers.txt") as tetramers_file:
            for line in tetramers_file.readlines():
                f_list = np.array([float(i)
                                   for i in line.split(" ") if i.strip()])
                normalized_tetramer_profiles[i] = f_list
                i += 1

    else:

        kmer_inds_4, kmer_count_len_4 = compute_kmer_inds(4)

        pool = Pool(nthreads)
        record_tetramers = pool.map(
            count_kmers, [(seq, 4, kmer_inds_4, kmer_count_len_4) for seq in sequences])
        pool.close()

        normalized = [x[1] for x in record_tetramers]
        unnormalized = [x[0] for x in record_tetramers]

        i = 0

        for l in range(len(unnormalized)):
            tetramer_profiles[i] = unnormalized[l]
            i += 1

        with open(output_path + "contig_tetramers.txt", "w+") as myfile:
            for l in range(len(unnormalized)):
                for j in range(len(unnormalized[l])):
                    myfile.write(str(unnormalized[l][j]) + " ")
                myfile.write("\n")

        i = 0

        for l in range(len(normalized)):
            normalized_tetramer_profiles[i] = normalized[l]
            i += 1

        with open(output_path + "normalized_contig_tetramers.txt", "w+") as myfile:
            for l in range(len(normalized)):
                for j in range(len(normalized[l])):
                    myfile.write(str(normalized[l][j]) + " ")
                myfile.write("\n")

    return normalized_tetramer_profiles


def get_cov_len(contigs_file, contig_names_rev, abundance_file):

    coverages = {}

    contig_lengths = {}

    i = 0

    sequences = []

    for index, record in enumerate(SeqIO.parse(contigs_file, "fasta")):

        contig_num = contig_names_rev[record.id]

        length = len(record.seq)

        contig_lengths[contig_num] = length

        sequences.append(str(record.seq))

        i += 1

    with open(abundance_file, "r") as my_abundance:
        for line in my_abundance:
            strings = line.strip().split("\t")

            contig_num = contig_names_rev[strings[0]]

            for i in range(1, len(strings)):

                contig_coverage = float(strings[i])

                if contig_coverage < 1:
                    contig_coverage = VERY_SMALL_VAL

                if contig_num not in coverages:
                    coverages[contig_num] = [contig_coverage]
                else:
                    coverages[contig_num].append(contig_coverage)

    n_samples = len(coverages[0])

    return sequences, coverages, contig_lengths, n_samples


def get_cov_len_megahit(contigs_file, contig_names_rev, graph_to_contig_map_rev, abundance_file):

    coverages = {}

    contig_lengths = {}

    i = 0

    sequences = []

    for index, record in enumerate(SeqIO.parse(contigs_file, "fasta")):
        contig_num = contig_names_rev[graph_to_contig_map_rev[record.id]]
        length = len(record.seq)
        contig_lengths[contig_num] = length
        sequences.append(str(record.seq))
        i += 1

    with open(abundance_file, "r") as my_abundance:
        for line in my_abundance:
            strings = line.strip().split("\t")

            contig_num = contig_names_rev[graph_to_contig_map_rev[strings[0]]]

            for i in range(1, len(strings)):

                contig_coverage = float(strings[i])

                if contig_coverage < VERY_SMALL_VAL:
                    contig_coverage = VERY_SMALL_VAL

                if contig_num not in coverages:
                    coverages[contig_num] = [contig_coverage]
                else:
                    coverages[contig_num].append(contig_coverage)

    n_samples = len(coverages[0])

    return sequences, coverages, contig_lengths, n_samples


def get_bin_profiles(bins, coverages, normalized_tetramer_profiles):

    bin_tetramer_profile = {}
    bin_coverage_profile = {}

    for b in bins:

        coverage_b = []
        tetramer_b = []

        for contig in bins[b]:
            coverage_b.append(coverages[contig])
            tetramer_b.append(normalized_tetramer_profiles[contig])

        coverage_b = np.array(coverage_b)
        tetramer_b = np.array(tetramer_b)

        bin_coverage_profile[b] = np.mean(coverage_b, axis=0)
        bin_tetramer_profile[b] = np.mean(tetramer_b, axis=0)

    return bin_tetramer_profile, bin_coverage_profile
