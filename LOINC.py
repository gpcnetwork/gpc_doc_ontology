LOINC_TYPE_ORDER = ['Document.SubjectMatterDomain','Document.Kind','Document.Setting','Document.TypeOfService', 'Document.Role']

class LOINC(object):
    lexicon_list = []

    # code_value = ""
    # number_of_part_numbers = 0
    # number_of_real_part_numbers = 0
    # bags_of_words = {} # Key: 'SMD', 'KOD', etc #Value = "a bag of words for
    # number_of_words = {} # Key: 'SMD', "KOD', etc # values is a number for the number of terms in the bag...
    # fake_dim = {}
    def __init__(self, code_value, BOW, BOW_count, number_of_part_numbers, number_of_real_part_numbers, bags_of_words, number_of_words, fake_dim):
        self.code_value = code_value
        self.BOW = BOW
        self.BOW_count = BOW_count
        self.number_of_part_numbers = number_of_part_numbers
        self.number_of_real_part_numbers = number_of_real_part_numbers
        self.bags_of_words = bags_of_words
        self.number_of_words = number_of_words
        self.fake_dim = fake_dim
        self.priority = 100
    def __repr__(self):
        string = "LOINC CODE: " + self.code_value + ".\n"
        string += f"The CODE has {self.number_of_part_numbers} dimensions and {self.number_of_real_part_numbers} real dimensions.\n\nLOINC DIMENSION AND PART NAMES\n"
        for type in LOINC_TYPE_ORDER:
            if type in self.number_of_words.keys():
                if self.number_of_words[type] > 0:
                    string += type + f" has {self.number_of_words[type]} {self.fake_dim[type]}words in its bag: "
                    for i in range(len(self.bags_of_words[type])):
                        if self.bags_of_words[type][i] > 0:
                            pass
                            #TODO: add printing functionality here.
                            string += self.lexicon_list[i] + ","
                    string += "\n"
        return string