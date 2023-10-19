import numpy as np


def bag_to_np_array(bag, lexicon_list):
    array = []
    for word in lexicon_list:
        array.append(bag[word])
    return np.array(array)


def string_to_bag(string, ll):
    tokenized_string = string.lower().split(' ')
    return token_string_to_bag(tokenized_string, ll)


def token_string_to_bag(tokenized_array, ll):
    # Receives an array of lower case words that it converts into a bag of words
    bag = dict.fromkeys(ll, 0)
    for word in tokenized_array:
        bag[word] = 1

    return bag


# BAG Matching-Functions
dims_filled_no_loinc = [0] * 7
dims_filled_no_loinc_till_note_added = [0] * 7
def find_best_match(note, loinc_BOW, lexicon_list, force_note=False):
    best_code = ""
    best_priority = 0
    best_code_dim_count = 0
    dims_fulfilled = 0
    most_dims_filled = -1

    # If most dimensions filled is greater than/equal to 2
    # and no LOINC match AND if the note doesn't have a "note" or "report" descriptor in it,
    # we'll add them and run again

    for Key in loinc_BOW:  # For each loinc code
        # If we already found a matching LOINC Code with four parts, we don't need to look at loinc codes with 4 parts or less.
        if loinc_BOW[Key].number_of_real_part_numbers < best_code_dim_count:
            continue

        sc = np.dot(note, loinc_BOW[Key].BOW)
        if sc / loinc_BOW[Key].BOW_count <= 0.5: #If there isn't sufficient number of matching, just ignore.
            continue
            
        # look at each dimension of each loinc code.
        for dim in loinc_BOW[Key].bags_of_words:
            sc = np.dot(note, loinc_BOW[Key].bags_of_words[dim])
            if sc / loinc_BOW[Key].number_of_words[dim] >= 0.60 and loinc_BOW[Key].fake_dim[dim] == False:
                dims_fulfilled += 1

        # If each dimension of the loinc code is fulfilled by the note, then it is marked as the best note so far.
        if dims_fulfilled >= loinc_BOW[Key].number_of_real_part_numbers and loinc_BOW[Key].priority >= best_priority:
            best_code = loinc_BOW[Key].code_value
            best_priority = loinc_BOW[Key].priority
            best_code_dim_count = loinc_BOW[Key].number_of_real_part_numbers
        if dims_fulfilled > most_dims_filled:
            most_dims_filled = dims_fulfilled
        dims_fulfilled = 0

    if best_code == "" and force_note == False:
        dims_filled_no_loinc[dims_fulfilled] += 1
        if most_dims_filled > 4:
            note[lexicon_list.index("report")] = 1
            note[lexicon_list.index("note")] = 1
            ret = find_best_match(note,loinc_BOW,lexicon_list, True)
            if ret != "":
                dims_filled_no_loinc_till_note_added[most_dims_filled] += 1
            return ret
    else:
        return best_code


# This is for testing. Checks a note against a specified loinc code and gets the number of dimensions matched
def find_match(note, loinc_code, loinc_BOW):
    dims_fulfilled = 0
    for dim in loinc_BOW[loinc_code].bags_of_words:
        sc = np.dot(note, loinc_BOW[loinc_code].bags_of_words[dim])
        if sc / loinc_BOW[loinc_code].number_of_words[dim] >= 0.60 and loinc_BOW[loinc_code].fake_dim[dim] == False:
            print(sc, dim)
            dims_fulfilled += 1
    print(dims_fulfilled, loinc_BOW[loinc_code].number_of_real_part_numbers)
