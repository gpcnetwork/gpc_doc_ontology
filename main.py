from datetime import datetime
from itertools import repeat
import json
from multiprocessing import Pool, RLock, cpu_count
import os
import sys
import traceback
from typing import Iterable, Optional
import pandas as pd
import numpy as np
import csv
import time
import re
from tqdm import tqdm
from LOINC import *
from bag_of_words import *
import utils.Logger as Logger
import utils.hashing as md5


DIR = sys.path[0]
CONFIGS_EXAMPLE = os.path.join(DIR, "configs", "config_example.json")
CONFIGS_FILE = os.path.join(DIR, "configs", "config.json")
LOGS_FOLDER = os.path.join(DIR, "logs")
INPUT_FOLDER = os.path.join(DIR, "input")
OUTPUT_FOLDER = os.path.join(DIR, "output")
CONFIGS = None
LOGGER = None

def apply_note_BOW(row, synonyms, lexicon_list, df_columns):
    note_str = ""
    for col in df_columns:
        note_str += str(row[col]) + " "

    note_str = note_str.replace("General Message", "Note")
    note_str = note_str.replace("Social Work Narrative", "Function Status Note")
    note_str = note_str.replace("Social Services Notes", "Function Status Note")

    note_str = note_str.lower()
    tokenized_note_str = re.findall(r"[\w]+", note_str)

    if CONFIGS["USE_SYNONYMS"] is True:
        for key in synonyms.keys():
            if note_str.find(key) > -1:
                for word in synonyms[key].split(" "):
                    tokenized_note_str.append(word)

    tokenized_note_str.append("{setting}")
    tokenized_note_str.append("{role}")
    BOW = bag_to_np_array(
        token_string_to_bag(tokenized_note_str, lexicon_list), lexicon_list
    )

    bow_str = ""
    for j in range(len(BOW)):
        if BOW[j] > 0:
            bow_str += lexicon_list[j] + " "
    return bow_str


def load_lexicon_list(refresh=False):
    #  TODO: Add logic to create a file so this \
    #   doesn't have to be repeated everytime and we can just read from the file
    try:
        LOGGER.info(
            f"Loading LOINC lexicon from: {os.path.join(DIR, 'configs', CONFIGS['LOINC_SOURCE'])}"
        )
        doc_ont = pd.read_csv(os.path.join(DIR, "configs", CONFIGS["LOINC_SOURCE"]))

        cur_code = doc_ont["LoincNumber"][0]
        lexicon = set()
        tokenized_loinc_description = ""

        for i in doc_ont.index:
            if doc_ont["LoincNumber"][i] == cur_code:
                # add to tokenized_loinc_description
                tokenized_loinc_description += doc_ont["PartName"][i] + " "
            else:
                tokenized_loinc_description = tokenized_loinc_description.lower()
                lexicon.update(tokenized_loinc_description.split(" "))
                tokenized_loinc_description = doc_ont["PartName"][i] + " "
                cur_code = doc_ont["LoincNumber"][i]

        lexicon_list = []
        for i in lexicon:
            lexicon_list.append(i)

        lexicon_list.remove("")  # This is an ordered list
        lexicon_list.remove("care")
        lexicon_list.remove("of")
        lexicon_list.remove(
            "wound,"
        )  # Remove these two words because they have a comma at the end, causing numbers to be a little off...
        lexicon_list.append("wound")
        lexicon_list.remove("ostomy,")
        lexicon_list.append("ostomy")

        LOGGER.debug(f"Lexicon List has {len(lexicon_list)} numbers")
        return lexicon_list
    except:
        LOGGER.error(f"Failed to load LOINC lexicon: \n{traceback.format_exc()}")
        sys.exit(1)

def load_loinc_names():
    try:
        LOGGER.info(
            f"Loading LOINC lexicon from: {os.path.join(DIR, 'configs', CONFIGS['LOINC_NAMES'])}"
        )
        loinc_names = pd.read_csv(os.path.join(DIR, "configs", CONFIGS["LOINC_NAMES"]))
        return loinc_names
    except:
        LOGGER.error(f"Failed to load LOINC names: \n{traceback.format_exc()}")
        sys.exit(1)

def generate_loinc_BOW(lexicon_list):
    try:  # generate LOINC bag of words
        LOGGER.info(
            f"Generating bags of words for lexicon using: {os.path.join(DIR, 'configs', CONFIGS['LOINC_SOURCE'])}"
        )
        doc_ont = pd.read_csv(os.path.join(DIR, "configs", CONFIGS["LOINC_SOURCE"]))
        cur_code = doc_ont["LoincNumber"][0]

        loinc_BOW = {}

        # Used for object creation
        bags_of_words = {}
        number_of_words = {}
        number_of_part_numbers = 0
        number_of_real_part_numbers = 0

        cur_part_type_name = doc_ont["PartTypeName"][0]
        concatenated_part_name_string = ""
        fake_dim = {}
        BOW = ""
        for i in tqdm(doc_ont.index):
            if doc_ont["LoincNumber"][i] == cur_code:
                partTypeName = doc_ont["PartTypeName"][i]
                BOW += doc_ont["PartName"][i] + " "
                if partTypeName == cur_part_type_name:
                    concatenated_part_name_string += " " + doc_ont["PartName"][i]
                else:
                    number_of_words[cur_part_type_name] = len(
                        concatenated_part_name_string.split(" ")
                    )
                    bags_of_words[cur_part_type_name] = bag_to_np_array(
                        string_to_bag(concatenated_part_name_string, lexicon_list),
                        lexicon_list,
                    )
                    number_of_part_numbers += 1
                    if (
                        doc_ont["PartName"][i - 1] != "{Role}"
                        and doc_ont["PartName"][i - 1] != "{Setting}"
                    ):
                        number_of_real_part_numbers += 1
                    if (
                        doc_ont["PartName"][i - 1] == "{Role}"
                        or doc_ont["PartName"][i - 1] == "{Setting}"
                    ):
                        fake_dim[cur_part_type_name] = True
                    else:
                        fake_dim[cur_part_type_name] = False
                    cur_part_type_name = doc_ont["PartTypeName"][i]
                    concatenated_part_name_string = doc_ont["PartName"][i]
            else:
                number_of_words[cur_part_type_name] = len(
                    concatenated_part_name_string.split(" ")
                )
                bags_of_words[cur_part_type_name] = bag_to_np_array(
                    string_to_bag(concatenated_part_name_string, lexicon_list),
                    lexicon_list,
                )

                BOW_count = len(BOW.split(" "))
                BOW = bag_to_np_array(string_to_bag(BOW, lexicon_list), lexicon_list)

                if (
                    doc_ont["PartName"][i - 1] != "{Role}"
                    and doc_ont["PartName"][i - 1] != "{Setting}"
                ):
                    number_of_real_part_numbers += 1
                if (
                    doc_ont["PartName"][i - 1] == "{Role}"
                    or doc_ont["PartName"][i - 1] == "{Setting}"
                ):
                    fake_dim[cur_part_type_name] = True
                else:
                    fake_dim[cur_part_type_name] = False
                number_of_part_numbers += 1

                # Add all data into the dictionary for the loinc code
                lcode = LOINC(
                    cur_code,
                    BOW,
                    BOW_count,
                    number_of_part_numbers,
                    number_of_real_part_numbers,
                    bags_of_words,
                    number_of_words,
                    fake_dim,
                )
                loinc_BOW[cur_code] = lcode
                # Reset all variables
                number_of_part_numbers = 0
                number_of_real_part_numbers = 0
                bags_of_words = {}
                number_of_words = {}
                fake_dim = {}

                cur_code = doc_ont["LoincNumber"][i]
                cur_part_type_name = doc_ont["PartTypeName"][i]
                concatenated_part_name_string = doc_ont["PartName"][i]
                BOW = doc_ont["PartName"][i] + " "

        # Some Fine tuning of the LOINC Bag of words
        loinc_BOW[
            "34112-3"
        ].priority = 10  # A very generic hospital note, so assigning a low priority. Everything else has a default priority of 100.
        loinc_BOW["96339-7"].priority = 20
        loinc_BOW["75449-9"].priority = 30
        loinc_BOW["34109-9"].priority = 5  # Just a note... that's it
        loinc_BOW[
            "96345-4"
        ].priority = 10  # Outpatient summary note, gets in the way of outpatient discharge summaries...
        loinc_BOW["96335-5"].priority = 10  # gets in the way of DE Discharge summaries
        loinc_BOW["96344-7"].priority = 20
        loinc_BOW["96343-9"].priority = 50
        loinc_BOW["88645-7"].priority = 75
        loinc_BOW["84361-5"].priority = 40
        loinc_BOW["84377-1"].priority = 50
        loinc_BOW["68608-9"].priority = 20
        loinc_BOW["83800-3"].priority = 80  # physician hospital note
        loinc_BOW["75477-0"].priority = 60  # resident note
        loinc_BOW["75476-2"].priority = 70  # Physician note
        loinc_BOW["85266-5"].priority = 90

        # Removing 'discouraged'/'depricated' loinc codes
        loinc_BOW.pop("80563-0")
        loinc_BOW.pop("80562-2")
        loinc_BOW.pop("34109-9")
        len(loinc_BOW)

        return loinc_BOW
    except:
        LOGGER.error(
            f"Failed to generate bags of words for lexicon: \n{traceback.format_exc()}"
        )
        sys.exit(1)


def create_default_configs():
    configs = {
        "LOGGER_NAME": "doc_ontology",
        "LOGGER_FOLDER": None,
        "INPUT_FOLDER": None,
        "OUTPUT_FOLDER": None,
        "USE_INCLUSIONS": False,
        "USE_EXCLUSIONS": False,
        "USE_SYNONYMS": False,
        "CPUS": -1,  # any -# means use all except 1 CPU. Positive # means use that many CPUS or the max number available
        "INPUT_FILE": "CHANGEME.csv",
        "LOINC_SOURCE": "DocumentOntology_original.csv",
        "LOINC_NAMES": "ComponentHierarchyBySystem.csv",
        "SYNONYMS_FILE": "synonyms.csv",
        "APPENDED_FILENAME": "LOINC_MAPPINGS",
        "COUNT_COLUMN": "note_count",
        "EXLUDED_COLUMNS": ["note_count"],
        "INCLUDED_COLUMNS": [
            "author_role",
            "subject",
            "service",
            "setting",
            "doctype"
        ],
        "HASH_COLUMNS": [
            "author_role",
            "subject",
            "service",
            "setting",
            "doctype"
        ],
    }
    try:
        if not os.path.exists(CONFIGS_EXAMPLE):
            with open(CONFIGS_EXAMPLE, "w") as f:
                json.dump(configs, f, indent=4)
            print(f"Created example config file: {CONFIGS_EXAMPLE}")
        else:
            print(f"Example config file already exists: {CONFIGS_EXAMPLE}")
        return 0
    except:
        print(
            f"Error creating example config file ({CONFIGS_EXAMPLE}): {traceback.format_exc()}"
        )
        return 1


def load_synonyms():
    try:  # Read the synonym list
        synonyms = {}
        if CONFIGS["USE_SYNONYMS"]:
            LOGGER.info("Loading synonyms")
            with open(os.path.join(DIR, "configs", CONFIGS["SYNONYMS_FILE"])) as data:
                reader = csv.reader(data)
                data_read = [row for row in reader]
            for list in data_read:
                synonyms.update({list[0]: list[1]})
            LOGGER.info("Synonyms load completed")
        else:
            LOGGER.info("Skipping synonyms load")
        return synonyms
    except:
        LOGGER.error(f"Failed to read in synonyms: \n{traceback.format_exc()}")
        return {}


def load_notes_metadata(file):
    try:  # read notes metedata
        LOGGER.info(f"Reading in notes metadata from {file}")
        notes_df = pd.read_csv(file, index_col=0)
        notes_df = notes_df.fillna("")
        notes_df["BOW"] = ""
        notes_df["LOINC"] = ""
        notes_df["LOINC_NAME"] = ""
        return notes_df
    except:
        LOGGER.error(f"Failed to read in notes metadata: \n{traceback.format_exc()}")
        return None


def map_loinc_codes(notes_df_input, lexicon_list, loinc_names, loinc_bow, pid):
    try:  # map notes to LOINC codes
        BOW_LOINC_Dict = {}  # Where key is bag of word and value is a loinc CODE
        notes_df_output = notes_df_input.copy(deep=True)
        notes_df_output = notes_df_output.reset_index()
        tqdm_text = "Chunk #" + "{}".format(pid).zfill(2)
        with tqdm(
            total=len(notes_df_output), desc=tqdm_text, position=pid, leave=False
        ) as pbar:
            # for i in tqdm(range(len(notes_df_output)), desc=tqdm_text, position=pid):
            for i in range(len(notes_df_output)):
                bow = notes_df_output["BOW"][i]
                if bow in BOW_LOINC_Dict.keys():
                    notes_df_output.at[i, "LOINC"] = BOW_LOINC_Dict[bow]
                    #notes_df_output.at[i, "LOINC_NAME"] = loinc_names.loc[loinc_names['CODE'] == BOW_LOINC_Dict[bow]]#['CODE_TEXT'].values[0]
                else:
                    tokenized_note_str = bow.split(" ")
                    note_np = bag_to_np_array(
                        token_string_to_bag(tokenized_note_str, lexicon_list),
                        lexicon_list,
                    )
                    code = find_best_match(note_np, loinc_bow, lexicon_list)
                    BOW_LOINC_Dict[bow] = code
                    notes_df_output.at[i, "LOINC"] = code
                    #if code:
                    #    notes_df_output.at[i, "LOINC_NAME"] = loinc_names.loc[loinc_names['CODE'] == code]['CODE_TEXT'].values[0]
                if notes_df_output.at[i, "LOINC"]:
                    notes_df_output.at[i, "LOINC_NAME"] = loinc_names.loc[loinc_names['CODE'] == notes_df_output.at[i, "LOINC"]]['CODE_TEXT'].values[0]
                pbar.update(1)
        return notes_df_output
    except:
        print(
            f"Failed to map notes to LOINC codes for chunk {pid}: \n{traceback.format_exc()}"
        )
        sys.exit(1)


def log_mapping_coverage(notes_df_input):
    try:  # Print estimate percentage coverage
        LOGGER.info("Calculating coverage percentage and replacing NANs")
        aggregate = 0
        total = 0
        notes_df_output = notes_df_input.fillna("", inplace=False)
        for i in range(len(notes_df_output)):
            # cast the number as a string just in case so we can remove commas
            number = int(str(notes_df_output[CONFIGS["COUNT_COLUMN"]][i]).replace(',',''))
            total += number
            if notes_df_output["LOINC"][i].strip() != "":
                aggregate += number
        LOGGER.info(f"{(aggregate / total) * 100}% coverage of notes")
    except:
        LOGGER.error(
            f"Failed to calculate mapping coverage percentage: \n{traceback.format_exc()}"
        )


def write_csv(notes_df_input):
    try:  # Save work to file.
        filename = os.path.splitext(CONFIGS["INPUT_FILE"])[0]
        timestamp = time.strftime("%Y_%m_%d_%H%M%S")
        output_file = os.path.join(
            OUTPUT_FOLDER, f"{filename}_{CONFIGS['APPENDED_FILENAME']}_{timestamp}.csv"
        )
        LOGGER.info(f"Creating output file: {output_file}")
        # add columns
        notes_df_input['valid'] = np.nan
        notes_df_input['comment'] = np.nan
        notes_df_input = md5.add_md5_hash_column(notes_df_input, "md5", CONFIGS["HASH_COLUMNS"])
        notes_df_input.to_csv(output_file, index=False)
    except:
        LOGGER.error(f"Failed to generate output files: \n{traceback.format_exc()}")


def main():
    global LOGGER, LOGS_FOLDER, INPUT_FOLDER, OUTPUT_FOLDER, CONFIGS, CONFIGS_EXAMPLE, CONFIGS_FILE
    if create_default_configs():  # create default configsx
        sys.exit(1)
    try:  # load configs and check if they are present
        with open(CONFIGS_FILE, "r") as file:
            CONFIGS = json.load(file)
    except FileNotFoundError:
        print(f"Config file {CONFIGS_FILE} was not found. Ensure this file exists ")
    except:
        print(f"Failed to load configs: \n{traceback.format_exc()}")
    if CONFIGS is None:
        print("No configs loaded. Config file empty? Exiting")
        sys.exit(1)

    try:  # create logger
        LOGS_FOLDER = (
            LOGS_FOLDER
            if CONFIGS["LOGGER_FOLDER"] is None
            else CONFIGS["LOGGER_FOLDER"]
        )
        LOGGER = Logger.build_logger(name=CONFIGS["LOGGER_NAME"], directory=LOGS_FOLDER)
        LOGGER.info(f"Logger created and logging to {LOGS_FOLDER}")
    except:
        print(f"Error creating logger: \n{traceback.format_exc()}")
    if LOGGER is None:
        print("No logger instantiated. Exiting")
        sys.exit(1)

    try:  # set input/output folder
        INPUT_FOLDER = (
            INPUT_FOLDER
            if CONFIGS["INPUT_FOLDER"] is None
            else CONFIGS["LOGGER_FOLDER"]
        )
        OUTPUT_FOLDER = (
            OUTPUT_FOLDER
            if CONFIGS["OUTPUT_FOLDER"] is None
            else CONFIGS["OUTPUT_FOLDER"]
        )
    except KeyError:
        LOGGER.warn(
            f"Failed to get input and output folders from configs: \n{traceback.format_exc()}"
        )
        INPUT_FOLDER = os.path.join(DIR, "input")
        OUTPUT_FOLDER = os.path.join(DIR, "output")
    LOGGER.debug(f"Input folder is: {INPUT_FOLDER}")
    LOGGER.debug(f"Output folder is: {OUTPUT_FOLDER}")

    total_start_time = datetime.now()
    LOGGER.info(f"Starting processing at :{total_start_time}")
    # load synonyms and input file
    synonyms = load_synonyms()
    notes_df = load_notes_metadata(os.path.join(INPUT_FOLDER, CONFIGS["INPUT_FILE"]))

    if notes_df is None:
        LOGGER.info("Notes metadata is empty. Exiting.")
        sys.exit(1)
    # load LOINC lexicon and names
    LOINC.lexicon_list = load_lexicon_list()
    LOINC_BOW = generate_loinc_BOW(LOINC.lexicon_list)
    LOINC_NAMES = load_loinc_names()
    df_columns = []
    if CONFIGS["USE_INCLUSIONS"] == CONFIGS["USE_EXCLUSIONS"] == True:
        raise ValueError("Cannot use column inclusions and exclusions simultaneously")
    elif CONFIGS["USE_INCLUSIONS"]:
        df_columns = CONFIGS["INCLUDED_COLUMNS"]
    elif CONFIGS["USE_EXCLUSIONS"]:
        df_columns = []
        excluded_cols = CONFIGS["EXLUDED_COLUMNS"]
        excluded_cols += ["BOW", "LOINC", "LOINC_NAME", CONFIGS["COUNT_COLUMN"]]
        for column in notes_df.columns:
            if column not in CONFIGS["EXLUDED_COLUMNS"]:
                df_columns.append(column)
    else:  # use neither inclusions nor exclusions: use all columns that aren't ints nor the bow/loinc columns
        for column in notes_df.columns:
            if column not in [
                "BOW",
                "LOINC",
                "LOINC_NAME",
                CONFIGS["COUNT_COLUMN"],
            ] and not np.issubdtype(notes_df[column].dtype, int):
                df_columns.append(column)

    tqdm.pandas()  # Enables progress_apply function. quite a nifty library!
    LOGGER.info(
        f"Generating bags of words for note metadata: {len(notes_df)} rows to parse"
    )
    notes_df["BOW"] = notes_df.progress_apply(
        apply_note_BOW,
        axis=1,
        args=(
            synonyms,
            LOINC.lexicon_list,
            df_columns,
        ),
    )

    # this works
    tic = datetime.now()
    num_processes = cpu_count()
    if CONFIGS["CPUS"] > 0 and CONFIGS["CPUS"] <= cpu_count():
        num_processes = CONFIGS["CPUS"]
    LOGGER.info(f"Using {num_processes} processes/cpus for {num_processes} chunks.")
    split_notes_mapped_df = np.array_split(notes_df, num_processes)
    pids = [num for num in range(num_processes)]
    with Pool(
        processes=num_processes, initargs=(RLock(),), initializer=tqdm.set_lock
    ) as pool:
        results = pool.starmap(
            map_loinc_codes,
            zip(
                split_notes_mapped_df,
                repeat(LOINC.lexicon_list),
                repeat(LOINC_NAMES),
                repeat(LOINC_BOW),
                pids,
            ),
        )
    print("", flush=True)  # clean up the terminal after tqdm; just a hack
    toc = datetime.now()
    LOGGER.info(f"Mapping duration was {toc-tic}")

    mapped_notes_df = pd.DataFrame()
    mapped_notes_df = pd.concat(results, ignore_index=True)
    log_mapping_coverage(mapped_notes_df)

    write_csv(mapped_notes_df)
    total_end_time = datetime.now()
    LOGGER.info(f"Total duration: {total_end_time - total_start_time}")


if __name__ == "__main__":
    main()
