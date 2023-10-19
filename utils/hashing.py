""" TAKEN FROM https://gist.github.com/knu2xs/c1a985e37e6e2d40fbb717f374c2a368 """
from hashlib import md5
import pandas as pd
from typing import Optional, Iterable

def get_md5_from_series(input_iterable: Iterable) -> str:
    """
    Create a MD5 hash from an Iterable, typically a row from a Pandas ``DataFrame``, but can be any
    Iterable object instance such as a list, tuple or Pandas ``Series``.
    
    Args:
        input_iterable: Typically a Pandas ``DataFrame`` row, but can be any Pandas ``Series``.
        
    Returns:
        MD5 hash created from the input values.
    """
    # convert all values to string, concantenate, and encode so can hash
    full_str = ''.join(map(str, input_iterable)).encode('utf-8')
    
    # create a md5 hash from the complete string
    md5_hash = md5(full_str).hexdigest()
    
    return md5_hash

    
def get_md5_series_from_dataframe(input_dataframe: pd.DataFrame, 
                                  columns: Optional[Iterable[str]] = None) -> pd.Series:
    """
    Create a Pandas ``Series`` of MD5 hashses for every row in a Pandas ``DataFrame``.
    
    Args:
        input_dataframe: Pandas ``DataFrame`` to be create MD5 hashes for.
        columns: If only wanting to use specific columns to calculate the hash, specify these here.
        
    Returns:
        MD5 hashes, one for every row in the input Pandas ``DataFrame``.
    """
    
    # if columns specified, filter to just these columns
    in_df = input_dataframe.loc[:,list(columns)] if columns is not None else input_dataframe
    
    # create md5 hash per row
    md5_hashes = in_df.apply(lambda row: get_md5_from_series(row), axis=1)
    
    return md5_hashes
    

def add_md5_hash_column(input_dataframe: pd.DataFrame, md5_column_name: str = 'md5_hash', 
                        columns: Optional[Iterable[str]] = None) -> pd.DataFrame:
    """
    Add a column to a Pandas ``DataFrame`` with a MD5 hash for every row.
    
    Args:
        input_dataframe: Pandas ``DataFrame`` to be create MD5 hashes for.
        md5_column_name: Name for the new column containing the MD5 hashes.
        columns: If only wanting to use specific columns to calculate the hash, specify these here.
        
    Returns:
        Copy of the input_dataframe with a new column containing the MD5 hash for every row.
    """
    
    # get the md5 hash
    md5_row = get_md5_series_from_dataframe(input_dataframe, columns)
    
    # copy the data frame and add new column
    out_df = input_dataframe.copy()
    out_df[md5_column_name] = md5_row
    
    return out_df