from __future__ import annotations
from typing import Dict
import sys
import re
import os.path
import glob
import logging.handlers
from sklearn.metrics import f1_score
from sklearn.metrics import precision_score
from sklearn.metrics import recall_score
import propaganda.src.article_annotations as aa
import propaganda.src.annotation as an

__author__ = "Giovanni Da San Martino"
__copyright__ = "Copyright 2019"
__credits__ = ["Giovanni Da San Martino"]
__license__ = "GPL"
__version__ = "0.1"
__maintainer__ = "Giovanni Da San Martino"
__email__ = "gmartino@hbku.edu.qa"
__status__ = "Beta"

logger = logging.getLogger("propaganda_scorer")


class Annotations(object):
    """
    Dictionary of Articles_annotations objects. 
    (basically a dataset of article_annotations objects)

    """

    def __init__(self, annotations:aa.Articles_annotations=None):

        if annotations is None:
            self.annotations:Dict[str, aa.Articles_annotations] = {} 
        else:
            self.annotations = annotations


    def __len__(self):
        """
        Returns the number of articles in the object
        """
        return len(self.get_article_id_list())


    def add_annotation(self, annotation:an.Annotation, article_id:str):
        """
        Add a single annotation to the article with id article_id. 
        If such article does not exists, the annotation is created. 
        """
        if not self.has_article(article_id):
            self.create_article_annotations_object(article_id)
        self.annotations[article_id].add_annotation(annotation)


    def check_overlapping_annotation_spans(self, prop_vs_non_propaganda, merge_overlapping_spans=False)->bool:
        """
        Check whether there are overlapping spans for the same technique in the same article.
        Two spans are overlapping if their associated techniques match (according to category_matching_func)
        If merge_overlapping_spans==True then the overlapping spans are merged, otherwise an error is raised.

        :param merge_overlapping_spans: if True merges the overlapping spans
        :return:
        """

        for article_id in self.get_article_id_list():

            if not self.get_article_annotations_obj(article_id).has_overlapping_spans(prop_vs_non_propaganda, merge_overlapping_spans):
                return False

            #annotation_list = self.get_article_annotations_obj(article_id).groupby_technique()
            #print(annotation_list)
            #if merge_overlapping_spans:
            #    for technique in annotation_list.keys():
            #        for i in range(1, len(annotation_list[technique])):
            #            annotation_list[technique][i].merge_spans(annotation_list[technique], i-1)
            #if not self.get_article_annotations_obj(article_id):
            #    return False
            # annotation_list = {}
            # for annotation in self.annotations.get_article_annotations(article_id):
            #     technique = annotation.get_label()
            #     if technique not in annotation_list.keys():
            #         annotation_list[technique] = [[technique, curr_span]]
            #     else:
            #         if merge_overlapping_spans:
            #             annotation_list[technique].append([technique, curr_span])
            #             merge_spans(annotation_list[technique], len(annotation_list[technique]) - 1)
            #         else:
            #             for matching_technique, span in annotation_list[technique]:
            #                 if len(curr_span.intersection(span)) > 0:
            #                     logger.error("In article %s, the span of the annotation %s, [%s,%s] overlap with "
            #                                  "the following one from the same article:%s, [%s,%s]" % (
            #                                  article_id, matching_technique,
            #                                  min(span), max(span), technique, min(curr_span), max(curr_span)))
            #                     return False
            #             annotation_list[technique].append([technique, curr_span])
            # if merge_overlapping_spans:
            #     annotations[article_id] = []
            #     for technique in annotation_list.keys():
            #         annotations[article_id] += annotation_list[technique]
        return True


    def compare_annotations_article_lists(self, second_annotations:Annotations)->bool:
        #checking that the number of articles for which the user has submitted annotations is correct
        secondAnnArticleIDlist = second_annotations.get_article_id_list()
        articleIDlist = self.get_article_id_list()
        if (len(secondAnnArticleIDlist) < len(articleIDlist)):
        #if len(gold_annotations.keys()) < len(submission_annotations.keys()):
            logger.error("The number of articles in the submission, %d, is greater than the number of articles in the "
                         "reference dataset" % (len(articleIDlist), len(secondAnnArticleIDlist))); 
            return False
        # logger.debug("OK: number of articles in the submission for %s is the same as the one in the gold file: %d"
        #              % (task_name, len(gold_annotations.keys())))
        #check that all file names are correct
        errors = [ article_id for article_id in articleIDlist if article_id not in secondAnnArticleIDlist ]
        if len(errors)>0:
            logger.error("The following article_ids in the submission file do not have a correspondence in the reference "
                        "dataset: %s\n" % (str(errors)))
            return False
        logger.debug("OK: all article ids have a correspondence in the list of articles from the reference dataset")
        return True

    def compare_annotations_identical_article_lists(self, second_annotations:Annotations):
        """
        Compare if self and <second_annotations> have identical article id lists
        :return: True if the lists are identical and False otherwise. 
        """
        #checking that the number of articles in self and <second_annotations> is the same
        if len(self.get_article_id_list()) != len(second_annotations.get_article_id_list()):
            logger.error("The number of articles in the annotations is different: %d, %d" 
                % (len(self.get_article_id_list()), len(second_annotations.get_article_id_list())))
            print(self.get_article_id_list())
            print(second_annotations.get_article_id_list())
            return False
        diff = set(self.get_article_id_list()).difference(set(second_annotations.get_article_id_list()))
        if len(diff) > 0:
            logger.error("The two lists of article ids differ: %s"%(diff))
            return False

        logger.debug("OK: the list of article ids in the two sets of annotations is identical")
        return True


    def compare_annotations_identical(self, second_annotations:Annotations)->bool:
        """
        Compare if self and <second_annotations> have identical annotations (without considering the technique labels)
        :return: True if the lists are identical and False otherwise. 
        """
        for article_id in self.get_article_id_list():
            an1_article_annotations = self.get_article_annotations_list(article_id)
            an2_article_annotations = second_annotations.get_article_annotations_list(article_id)
            if len(an1_article_annotations) != len(an2_article_annotations):
                logger.error("The number of annotations for article %s differs: %d vs %d"%(article_id, len(an1_article_annotations), len(an2_article_annotations)))
                return False
            for an1, an2 in zip(an1_article_annotations, an2_article_annotations):
                if not an1.is_span_equal_to(an2):
                    logger.error("The spans of the annotations of article %s do not match: [%s, %s] vs [%s, %s]"%(article_id, an1.get_start_offset(), an1.get_end_offset(), an2.get_start_offset(), an2.get_end_offset()))
                    return False
        return True


    def compute_span_score(self, second_annotations:Annotations, spans_only=False, per_article_evaluation=False):

        if an.Annotation.propaganda_techniques is None and not spans_only: #raise an error
            logger.error("ERROR: propaganda techniques list not loaded")
            return None

        prec_denominator = len(self.get_full_list_of_annotations())
        rec_denominator = len(second_annotations.get_full_list_of_annotations())
        technique_names = an.Annotation.propaganda_techniques.get_propaganda_techniques_list()
        technique_Spr_prec = {propaganda_technique: 0 for propaganda_technique in technique_names}
        technique_Spr_rec = {propaganda_technique: 0 for propaganda_technique in technique_names}
        cumulative_Spr_prec, cumulative_Spr_rec = (0, 0)
        f1_articles = []
        aa.Articles_annotations.set_output_format_article_id(True)
        aa.Articles_annotations.set_output_format_article_label(True)
        aa.Articles_annotations.set_output_format_article_spans(True)

        for example_id in self.get_article_id_list():
            second_ann_example_obj = second_annotations.get_article_annotations_obj(example_id)
            ann_example_obj = self.get_article_annotations_obj(example_id)
            logger.debug("Computing contribution to the score of example id %s and tuples\n%s\n%s\n"
                        % (example_id, ann_example_obj.annotations_to_string_csv(), second_ann_example_obj.annotations_to_string_csv()))

            article_cumulative_Spr_prec, article_cumulative_Spr_rec = (0, 0)
            #for j, sd in enumerate(submission_annotations[article_id]): #submission annotations for article article_id:
            for j, ann in enumerate(ann_example_obj.get_article_annotations()): 
                s=""
                ann_length = len(ann)
                for i, s_ann in enumerate(second_ann_example_obj):
                    if spans_only or ann.get_label()==s_ann.get_label():
                        #s += "\tmatch %s %s-%s - %s %s-%s"%(sd[0],sd[1], sd[2], gd[0], gd[1], gd[2])
                        intersection = ann.span_intersection(s_ann)
                        s_ann_length = len(s_ann)
                        Spr_prec = intersection/ann_length
                        article_cumulative_Spr_prec += Spr_prec
                        cumulative_Spr_prec += Spr_prec
                        s += "\tmatch %s %s-%s - %s %s-%s: S(p,r)=|intersect(r, p)|/|p| = %d/%d = %f (cumulative S(p,r)=%f)\n"\
                            %(ann.get_label(),ann.get_start_offset(), ann.get_end_offset(), s_ann.get_label(), s_ann.get_start_offset(), s_ann.get_end_offset(), intersection, ann_length, Spr_prec, cumulative_Spr_prec)
                        technique_Spr_prec[s_ann.get_label()] += Spr_prec

                        Spr_rec = intersection/s_ann_length
                        article_cumulative_Spr_rec += Spr_rec
                        cumulative_Spr_rec += Spr_rec
                        s += "\tmatch %s %s-%s - %s %s-%s: S(p,r)=|intersect(r, p)|/|r| = %d/%d = %f (cumulative S(p,r)=%f)\n"\
                            %(ann.get_label(),ann.get_start_offset(), ann.get_end_offset(), s_ann.get_label(), s_ann.get_start_offset(), s_ann.get_end_offset(), intersection, s_ann_length, Spr_rec, cumulative_Spr_rec)
                        technique_Spr_rec[s_ann.get_label()] += Spr_rec
                logger.debug("\n%s"%(s))

            p_article, r_article, f1_article = self.compute_prec_rec_f1(article_cumulative_Spr_prec,
                                                                len(ann_example_obj),
                                                                article_cumulative_Spr_rec,
                                                                len(second_ann_example_obj), False)
            f1_articles.append(f1_article)

        p,r,f1 = self.compute_prec_rec_f1(cumulative_Spr_prec, prec_denominator, cumulative_Spr_rec, rec_denominator)

        if per_article_evaluation:
            logger.info("Per article evaluation F1=%s"%(",".join([ str(f1_value) for f1_value in  f1_articles])))

        if not spans_only:
            f1_per_technique = []
            for technique_name in technique_Spr_prec.keys():
                prec_tech, rec_tech, f1_tech = self.compute_prec_rec_f1(technique_Spr_prec[technique_name],
                                            self.compute_technique_frequency(technique_name),
                                            technique_Spr_prec[technique_name],
                                            second_annotations.compute_technique_frequency(technique_name), False)
                f1_per_technique.append(f1_tech)
                logger.info("%s: P=%f R=%f F1=%f" % (technique_name, prec_tech, rec_tech, f1_tech))
            return p, r, f1, f1_per_technique

        return p, r, f1


    def compute_FLC_score(self, second_annotations:Annotations)->None:
            return self.compute_span_score(second_annotations)


    def compute_SI_score(self, second_annotations:Annotations, spans_only=True)->None:
            return self.compute_span_score(second_annotations)


    def FLC_score_to_string(self, second_annotations:Annotations, output_for_script=False):

        precision, recall, f1, f1_per_class = self.compute_FLC_score(second_annotations)
        res_for_screen = "\nF1=%f\nPrecision=%f\nRecall=%f\n%s\n" % (f1, precision, recall, "\n".join([ "F1_"+pr+"="+str(f)     for pr, f in zip(an.Annotation.propaganda_techniques.get_propaganda_techniques_list(), f1_per_class)]))
        if output_for_script:
            res_for_script = "%f\t%f\t%f\t"%(f1, precision, recall)
            res_for_script += "\t".join([ str(x) for x in f1_per_class])
        else:
            res_for_script = ""
        return res_for_screen, res_for_script


    def align_annotations(self, second_annotations:Annotations)->None:
        """
        Reorder all annotations such that the matching between annotations' labels
        and the ones from second_annotations is maximised. 
        """
        for article_id in second_annotations.get_article_id_list():
            self.get_article_annotations_obj(article_id).align_annotations(second_annotations.get_article_annotations_obj(article_id))


    def compute_prec_rec_f1(self, prec_numerator, prec_denominator, rec_numerator, rec_denominator, print_results=True):

        logger.debug("P=%f/%d, R=%f/%d"%(prec_numerator, prec_denominator, rec_numerator, rec_denominator))
        p, r, f1 = (0, 0, 0)
        if prec_denominator > 0:
            p = prec_numerator / prec_denominator
        if rec_denominator > 0:
            r = rec_numerator / rec_denominator
        if print_results: logger.info("Precision=%f/%d=%f\tRecall=%f/%d=%f" % (prec_numerator, prec_denominator, p,
                                                                            rec_numerator, rec_denominator, r))
        if prec_denominator == 0 and rec_denominator == 0:
            f1 = 1.0
        if p > 0 and r > 0:
            f1 = 2 * (p * r / (p + r))
        if print_results:
            logger.info("F1=%f" % (f1))
        return p,r,f1


    def compute_TC_score(self, second_annotations:Annotations):
        """
        second_annotations: gold labels
        """

        self.align_annotations(second_annotations)
        gold_labels = [ x.get_label() for x in second_annotations.get_full_list_of_annotations() ]
        submission_labels = [ x.get_label() for x in  self.get_full_list_of_annotations() ]

        precision = precision_score(gold_labels, submission_labels, pos_label=None, average='micro')
        recall = recall_score(gold_labels, submission_labels, pos_label=None, average='micro')
        f1 = f1_score(gold_labels, submission_labels, pos_label=None, average='micro')
        if an.Annotation.propaganda_techniques is not None:
            propaganda_techniques_list = an.Annotation.propaganda_techniques.get_propaganda_techniques_list_sorted()
            f1_per_class = f1_score(gold_labels, submission_labels, average=None, labels=propaganda_techniques_list)
            return precision, recall, f1, f1_per_class
        return precision, recall, f1


    def compute_technique_frequency(self, technique_name):
        return sum([ 1 for a in self.get_full_list_of_annotations() if a.get_label()==technique_name ])


    def create_article_annotations_object(self, article_id:str)->None:
        self.annotations[article_id] = aa.Articles_annotations(article_id=article_id)  


    def TC_score_to_string(self, second_annotation:Annotations, output_for_script=False):

            if an.Annotation.propaganda_techniques is None: #raise an error
                precision, recall, f1 = self.compute_TC_score(second_annotation)    
                res = "\nPrecision=%f\nRecall=%f\nF1=%f\n"%(precision, recall, f1)
            else:
                precision, recall, f1, f1_per_class = self.compute_TC_score(second_annotation)
                res_for_screen = "\nF1=%f\nPrecision=%f\nRecall=%f\n%s\n" % (precision, recall, f1, "\n".join([ "F1_"+pr+"="+str(f) for pr, f in zip(an.Annotation.propaganda_techniques.get_propaganda_techniques_list(), f1_per_class)]))
                if output_for_script:
                    res_for_script = "%f\t%f\t%f\t"%(f1, precision, recall)
                    res_for_script += "\t".join([ str(x) for x in f1_per_class])
                else:
                    res_for_script = ""
            return res_for_screen, res_for_script


    def get_full_list_of_annotations(self):
        full_list = []
        for article_id in self.get_article_id_list():
            for an in self.get_article_annotations_list(article_id):
                full_list.append(an)
        return full_list
            

    def has_article(self, article_id:str)->bool:
        """
        Check whether article_id is in the list of articles whose annotations are in the object. 
        """
        return article_id in self.get_article_id_list()


    def get_article_id_list(self):
        """
        All ids of the article in the object
        """
        return self.annotations.keys()


    def get_article_annotations_obj(self, article_id:str):
        """
        Returns all annotations of an article as an Article_annotations object.
        """
        return self.annotations[article_id]


    def get_article_annotations_list(self, article_id:str):
        """
        Returns all annotations of an article as a list of Annotation objects.
        """
        return self.annotations[article_id].get_article_annotations()


    def _guess_article_id_from_file_name(self, filename:str)->str:
        
        regex = re.compile("article([0-9]+).*")
        article_id = regex.match(os.path.basename(filename)).group(1)
        return article_id


    def load_annotation_list_from_file(self, filename):
        """
        Loads all annotations in file <filename>. The file is supposed to contain annotations for multiple articles. To load annotations for a single article use the function with the same name from module src.article_annotations. 
        Each annotation is checked according to check_format_of_annotation_in_file()
        """
        with open(filename, "r") as f:
            for i, line in enumerate(f.readlines(), 1):
                ann, article_id = an.Annotation.load_annotation_from_string(line.rstrip(), i, filename)
                if not ann.check_format_of_annotation_in_file():
                    sys.exit(logger.error("Annotation format not valid in file %s"%(filename)))                   
                self.add_annotation(ann, article_id)


    def load_annotation_list_from_folder(self, folder_name, pattern="*.labels"):
        """
        Loads all annotations from all files in folder <folder_name>. 
        Files in the folder are selected according to <pattern>
        """
        if not os.path.exists(folder_name):
            logger.error("trying to load annotations from folder %s, which does not exists"%(folder_name))
            return False
        if not os.path.isdir(folder_name):
            logger.error("trying to load annotations from folder %s, which does not appear to be a valid folder"%(folder_name))
            return False
        file_list = glob.glob(os.path.join(folder_name, pattern))
        if len(file_list) == 0:
            logger.error("Cannot load file list %s/%s"%(folder_name, pattern))
            sys.exit()
        for filename in file_list:
            self.create_article_annotations_object(self._guess_article_id_from_file_name(filename))
            self.load_annotation_list_from_file(filename)
        return True

#    def compute_technique_frequency(annotations_list, technique_name):
#        return sum([len([example_annotation for example_annotation in x if example_annotation[0] == technique_name])
#                    for x in self.a])


 #   def print_annotations(annotation_list):
 #       s = ""
 #       i=0
 #       for technique, span in annotation_list:
 #           s += "%d) %s: %d - %d\n"%(i, technique, min(span), max(span))
 #           i += 1
 #       return s
