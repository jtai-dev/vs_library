
# built-ins
import os
from collections import defaultdict

# external packages
import pandas
import numpy


def read_spreadsheet(filepath, **kwargs):

    """Reads a spreadsheet format file and converts it to pandas.DataFrame
    
    See more on pandas.DataFrame at:
    https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html
    
    Parameters
    ----------
    filepath : str
        Path to spreadsheet file on user's computer to be imported
    """

    _ , ext = os.path.splitext(filepath)

    try:
        if ext in ('.xls', '.xlsx', '.xlsm', '.xlsb', '.ods'):
            df = pandas.read_excel(filepath, **kwargs)

        elif ext == '.csv':
            df = pandas.read_csv(filepath, **kwargs)
        
        elif ext == '.tsv':
            df = pandas.read_table(filepath, **kwargs)
        
        else:
            df = pandas.DataFrame()
            return df, f"File not imported. Extension: \'{ext}\' not recognized"

        return df, f"File successfully imported as \'{os.path.basename(filepath)}\'"

    except Exception as e:
        
        df = pandas.DataFrame()

        return df, f"ERROR: {str(e)}"


def to_spreadsheet(df, filepath):

    """
    Converts a pandas.DataFrame into a spreadsheet file
    
    See more on pandas.DataFrame at:
    https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html

    Parameters
    ----------
    df : pandas.DataFrame()
        Not empty dataframe to be exported

    filepath : str
        Path on a user's computer where pandas.DataFrame() is to be exported
    """

    _ , ext = os.path.splitext(filepath)

    try:
        if ext in ('.ods', '.xlsx', '.xlsm', '.xlsb'):
            df.to_excel(filepath, index=False)

        elif ext == '.csv':
            df.to_csv(filepath, index=False)
        
        elif ext == '.tsv':
            df.to_csv(filepath, sep='\t', index=False)
        
        else:
            return False, f"File not exported. Extension: \'{ext}\' not recognized"

        return True, f"File successfully exported to \'{os.path.abspath(filepath)}\'"

    except Exception as e:
        return False, f"ERROR: {str(e)}"


def column_group_percentage(df, col):

    """
    Calculates the size percentage of a column group
    
    Returns
    -------
    pandas.Series

    """

    return df.groupby(col).size().apply(lambda x: x/len(df)*100)


def uniqueness(df):

    """
    Calculates the ratio of unique elements to the length of pandas.DataFrame
    in each column

    Returns
    -------
    pandas.Series
    """

    return df.nunique().apply(lambda x: x/len(df))


def adjusted_uniqueness(df, selected_cols):

    """
    Calculates the ratio of unique elements to length of pandas.DataFrame
    adjusted to selected columns
    
    Returns
    -------
    pandas.Series
    """

    u = df[selected_cols].nunique().apply(lambda x: x/len(df))
    return u.apply(lambda x: x / u.sum())


def get_column_dupes(df, column):

    """
    Finds for duplicates within a column
    
    Returns
    -------
    (duplicate row indices, duplicated row values)
    """
    # replace all blanks with NaN
    temp_df = df.replace('', numpy.nan)
    # keep is set to False so all duplicated values are accounted
    column_check = temp_df[column].duplicated(keep=False)

    # keep only duplicated rows and drop NaN
    df_dupe = temp_df[column_check].dropna(subset=[column])

    dupes_index = df_dupe.index.tolist()
    dupes = df_dupe[column].values.tolist()

    return dupes_index, dupes


def get_column_blanks(df, column):

    """
    Finds for blanks within a column
    
    Returns
    -------
    (blank row indices, blank row values)
    """

    # replace all blanks with NaN
    temp_df = df.replace('', numpy.nan)
    column_check = pandas.isnull(temp_df[column])
    
    # keep only blank rows
    df_blank = temp_df[column_check]

    blank_index = df_blank.index.tolist()
    blanks = df_blank[column].values.tolist()

    return blank_index, blanks


class PandasMatcher:

    def __init__(self):

        self.__df_to = pandas.DataFrame()
        self.__df_from = pandas.DataFrame()

        self.column_threshold = defaultdict(float)
        self.columns_to_match = defaultdict(list)
        self.columns_to_get = []
        
        # allowing columns to be grouped by the values found in it
        # [column_1, column_2, ...]
        self.column_groups = []

        self.required_threshold = 75.0
        self.cutoff = False

    @property
    def df_to(self):
        return self.__df_to

    @property
    def df_from(self):
        return self.__df_from

    @df_to.setter
    def df_to(self, df):
        self.__df_to = df.astype(str).replace('nan', '')
        self.columns_to_match.clear()

        for column_to in self.__df_to.columns:
            self.column_threshold[column_to] = self.required_threshold
            if column_to in self.__df_from.columns:
                self.columns_to_match[column_to].append(column_to)
            else:
                self.columns_to_match[column_to] = []

    @df_from.setter
    def df_from(self, df):
        self.__df_from = df.astype(str).replace('nan', '')
        self.columns_to_get.clear()

        for _, columns_from in self.columns_to_match.items():
            columns_from.clear()

        for column_from in self.__df_from.columns:
            if column_from in self.columns_to_match.keys():
                self.columns_to_match[column_from].append(column_from)

    @property
    def similarities(self):

        """
        Calculate the similarities of each column
        """

        # {column_from_1: (similarity_score, average_match_length),...}
        similarities = dict()

        for column in self.__df_to.columns:
            if column in self.__df_from.columns:
                full_length = len(set(self.__df_to[column]))
                intersected = len(set(self.__df_to[column]).intersection(set(self.__df_from[column])))

                score = round(intersected/full_length * 100, 2)
                average_rows_to_compare = len(self.__df_to)/intersected

                similarities[column] = (score, average_rows_to_compare)

        return similarities

    def _choices(self):
        
        choices = {}

        for column_to, columns_from in self.columns_to_match.items():
            for column_from in columns_from:
                if column_to not in choices.keys():
                    choices[column_to] = self.__df_from[column_from].copy()
                else:
                    choices[column_to] += ' ' + self.__df_from[column_from]

        return choices

    def __subset(self, row):
        """
        Grouped DataFrame by the values found in the comparative DataFrame
        """
        df = self.__df_from

        for group in self.column_groups:
            df = df[df[group]==row[group]]

        return df.index

    def _compute_score(self, choices, index_to, uniqueness):

        match_scores = defaultdict(float)
        row_to = self.__df_to.iloc[index_to]
        indices_to_compare = self.__subset(row_to)

        for column_to, columns_from in self.columns_to_match.items():

            if columns_from:
                value_to_compare = row_to[column_to]
                query = choices[column_to].iloc[indices_to_compare]
                if query.empty:
                    query = choices[column_to]

                matches = process.extract(value_to_compare, query,
                                          scorer=fuzz.WRatio,
                                          limit=len(self.__df_from),
                                          score_cutoff=0 if not self.cutoff 
                                                         else self.column_threshold[column_to])

                for _, score, index_from in matches:
                    match_scores[index_from] += score * uniqueness[column_to]

        return match_scores

    def _top_matches(self, match_scores, optimal_threshold):

        def filter_highest(y):
            return {k: v for k, v in y.items() if v == max(y.values())}

        top_matches = defaultdict(dict)

        for index_from, match_score in filter_highest(match_scores).items():

            if round(match_score, 2) >= round(self.required_threshold, 2):
                match_status = 'REVIEW' if match_score < optimal_threshold else 'MATCHED'
                top_matches[index_from].update({'match_status': match_status,
                                                'match_score': match_score})

        return top_matches

    def match(self):

        columns_to_match = [column for column in self.columns_to_match.keys() if self.columns_to_match[column]]
        uniqueness = adjusted_uniqueness(self.__df_to, columns_to_match)
        optimal_threshold = sum([self.column_threshold[column] * uniqueness[column] for column in columns_to_match])

        choices = self._choices()
        df_matched = self.__df_to.copy()

        scores = []

        for column in self.columns_to_get:
            if column not in df_matched.columns:
                df_matched[column] = ''

        df_matched['match_status'] = ''
        df_matched['row_index'] = ''
        df_matched['match_score'] = ''

        for index_to in tqdm(range(0, len(self.__df_to))):

            match_scores = self._compute_score(choices, index_to, uniqueness)
            top_matches = self._top_matches(match_scores, optimal_threshold)

            if len(top_matches) == 1:

                index_from = next(iter(top_matches))

                for column in self.columns_to_get:
                    df_matched.at[index_to, column] = self.__df_from.at[index_from, column]

                df_matched.at[index_to, 'row_index'] = int(index_from + 2)
                df_matched.at[index_to, 'match_score'] = top_matches[index_from]['match_score']
                df_matched.at[index_to, 'match_status'] = top_matches[index_from]['match_status']

                scores.append(top_matches[index_from]['match_score'])

            elif len(top_matches) > 1:

                df_matched.at[index_to, 'row_index'] = ', '.join([str(int(key) + 2) for key in top_matches.keys()])
                df_matched.at[index_to, 'match_status'] = 'AMBIGUOUS'

            else:
                df_matched.at[index_to, 'match_status'] = 'UNMATCHED'

        dupe_index, _ = get_column_dupes(df_matched, 'row_index')
        df_matched.loc[dupe_index, 'match_status'] = "DUPLICATES"

        m_stat = df_matched['match_status'].value_counts()

        m_info = {
            "Total Match Score": f"{round(m_stat['MATCHED']/len(self.__df_to) * 100, 2) if 'MATCHED' in m_stat.index else 0}%",
            "Average Match Score": f"{round(sum(scores)/len(scores), 2) if scores else 0}%",
            "Highest Match Score": f"{round(max(scores), 2) if scores else -1}%",
            "Lowest Match Score": f"{round(min(scores), 2) if scores else -1}%"
            }

        m_info.update(m_stat)
        return df_matched, m_info

