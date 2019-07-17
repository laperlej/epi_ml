import json
import collections
import io
import os.path

from data_source import EpiDataSource

class Metadata(object):
    def __init__(self, datasource: EpiDataSource):
        self._metadata = self._load_metadata(datasource.metadata_file)

    def __getitem__(self, md5):
        return self._metadata[md5]

    def __delitem__(self, md5):
        del self._metadata[md5]

    def __contains__(self, md5):
        return md5 in self._metadata

    def get(self, md5):
        return self._metadata.get(md5)

    @property
    def md5s(self):
        return self._metadata.keys()

    @property
    def datasets(self):
        return self._metadata.values()

    def _load_metadata(self, meta_file: io.IOBase):
        meta_file.seek(0)
        meta_raw = json.load(meta_file)
        metadata = {}
        for dataset in meta_raw["datasets"]:
            metadata[dataset["md5sum"]] = dataset
        return metadata

    def apply_filter(self, meta_filter=lambda item: True):
        #item is md5:dataset
        self._metadata = dict(filter(meta_filter, self._metadata.items()))

    def remove_missing_labels(self, label_category):
        """Remove datasets where the metadata category is missing."""
        filt = lambda item: label_category in item[1]
        self.apply_filter(filt)

    def md5_per_class(self, label_category):
        """Return {label/class:md5 list} dict for a given metadata category.

        Will fail if remove_missing_labels has not been ran before.
        """
        sorted_md5 = sorted(self._metadata.keys())
        data = collections.defaultdict(list)
        for md5 in sorted_md5:
            data[self._metadata[md5][label_category]].append(md5)
        return data

    def remove_small_classes(self, min_class_size, label_category):
        """Remove from metatada classes with less than min_class_size examples
        for a given metatada category.
        """
        data = self.md5_per_class(label_category)
        nb_class = len(data)

        nb_removed_class = 0
        for label, size in self.label_counter(label_category).most_common():
            if size < min_class_size:
                nb_removed_class += 1
                for md5 in data[label]:
                    del self._metadata[md5]

        print("{}/{} labels left after filtering.".format(nb_class - nb_removed_class, nb_class))

    def label_counter(self, label_category):
        counter = collections.Counter()
        for labels in self._metadata.values():
            label = labels[label_category]
            counter.update([label])
        return counter

    def display_labels(self, label_category):
        print('\nExamples')
        i = 0
        for label, count in self.label_counter(label_category).most_common():
            print('{}: {}'.format(label, count))
            i += count
        print('For a total of {} examples\n'.format(i))

    def create_healthy_category(self):
        """Combine "disease" and "donor_health_status" to create a "healthy" category.

        When a dataset has pairs with unknow correspondance, it does not add
        the category, and so these datasets are ignored through remove_missing_labels().
        """
        healthy_category = HealthyCategory()
        for dataset in self.datasets:
            healthy = healthy_category.get_healthy_status(dataset)
            if healthy == "?":
                continue
            dataset["healthy"] = healthy

    def merge_molecule_classes(self):
        """Combine similar classes pairs in the molecule category."""
        for dataset in self.datasets:
            molecule = dataset.get("molecule", None)
            if molecule == "rna":
                dataset["molecule"] = "total_rna"
            elif molecule == "polyadenylated_mrna":
                dataset["molecule"] = "polya_rna"


class HealthyCategory(object):
    """Create/Represent/manipulate the "healthy" metadata category"""
    def __init__(self):
        self.pairs_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "healthy_category.tsv"
            )
        self.healthy_dict = self.read_healthy_pairs()

    @staticmethod
    def get_healthy_pairs(datasets):
        """Return set of (disease, donor_health_status) pairs."""
        pairs = set([])
        for dataset in datasets:
            disease = dataset.get("disease", "--empty--")
            donor_health_status = dataset.get("donor_health_status", "--empty--")
            pairs.add((disease, donor_health_status))
        return pairs

    def list_healthy_pairs(self, datasets):
        """List unique (disease, donor_health_status) pairs."""
        for pair in sorted(self.get_healthy_pairs(datasets)):
            print("{}\t{}".format(*pair))

    def read_healthy_pairs(self):
        """Return a (disease, donor_health_status):healthy dict defined in
        a tsv file with disease|donor_health_status|healthy columns.
        """
        healthy_dict = {}
        with open(self.pairs_file, "r") as tsv_file:
            next(tsv_file) # skip header
            for line in tsv_file:
                disease, donor_health_status, healthy = line.rstrip('\n').split('\t')
                healthy_dict[(disease, donor_health_status)] = healthy
        return healthy_dict

    def get_healthy_status(self, dataset):
        """Return "y", "n" or "?" depending of the healthy status of the dataset."""
        disease = dataset.get("disease", "--empty--")
        donor_health_status = dataset.get("donor_health_status", "--empty--")
        return self.healthy_dict[(disease, donor_health_status)]
