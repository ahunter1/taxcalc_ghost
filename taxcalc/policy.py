"""
Tax-Calculator federal tax policy Policy class.
"""
# CODING-STYLE CHECKS:
# pep8 --ignore=E402 policy.py
# pylint --disable=locally-disabled --extension-pkg-whitelist=numpy policy.py
# (when importing numpy, add "--extension-pkg-whitelist=numpy" pylint option)


import os
import sys
import json
import re
import six
import numpy as np
from .parameters_base import ParametersBase


class Policy(ParametersBase):

    """
    Constructor for the federal tax policy class.

    Parameters
    ----------
    parameter_dict: dictionary of PARAM:DESCRIPTION pairs
        dictionary of policy parameters; if None, default policy
        parameters are read from the current_law_policy.json file.

    start_year: integer
        first calendar year for historical policy parameters.

    num_years: integer
        number of calendar years for which to specify policy parameter
        values beginning with start_year.

    inflation_rates: dictionary of YEAR:RATE pairs
        variable inflation rates used to project future policy parameter
        values; if None, default inflation rates (specified below) are used.

    wage_growth_rates: dictionary of YEAR:RATE pairs
        variable wage growth rates used to project future policy parameter
        values; if None, default wage growth rates (specified below) are used.

    Raises
    ------
    ValueError:
        if parameter_dict is neither None nor a dictionary.
        if num_years is less than one.
        if len(inflation_rates) is not equal to num_years.
        if min(inflation_rates.keys()) is not equal to start_year.

    Returns
    -------
    class instance: Policy
    """

    DEFAULTS_FILENAME = 'current_law_policy.json'
    JSON_START_YEAR = 2013  # remains the same unless earlier data added
    LAST_BUDGET_YEAR = 2026  # increases by one every calendar year
    DEFAULT_NUM_YEARS = LAST_BUDGET_YEAR - JSON_START_YEAR + 1

    # default price inflation rates by year
    __pirates = {2013: 0.0148, 2014: 0.0159, 2015: 0.0013, 2016: 0.0135,
                 2017: 0.0233, 2018: 0.0236, 2019: 0.0238, 2020: 0.0245,
                 2021: 0.0242, 2022: 0.0240, 2023: 0.0239, 2024: 0.0240,
                 2025: 0.0245, 2026: 0.0242}

    # default wage growth rates by year
    __wgrates = {2013: 0.0276, 2014: 0.0496, 2015: 0.0477, 2016: 0.0479,
                 2017: 0.0441, 2018: 0.0420, 2019: 0.0383, 2020: 0.0381,
                 2021: 0.0403, 2022: 0.0413, 2023: 0.0417, 2024: 0.0417,
                 2025: 0.0415, 2026: 0.0416}

    @staticmethod
    def default_inflation_rates():
        """
        Return complete default price inflation rate dictionary.

        Parameters
        ----------
        none

        Returns
        -------
        default inflation rates: dict
            decimal (not percentage) annual inflation rate by calendar year.
        """
        return Policy.__pirates

    @staticmethod
    def default_wage_growth_rates():
        """
        Return complete default wage growth rate dictionary.

        Parameters
        ----------
        none

        Returns
        -------
        default growth rates: dict
            decimal (not percentage) annual growth rate by calyear.
        """
        return Policy.__wgrates

    def __init__(self, parameter_dict=None,
                 start_year=JSON_START_YEAR,
                 num_years=DEFAULT_NUM_YEARS,
                 inflation_rates=None,
                 wage_growth_rates=None):
        """
        Policy class constructor.
        """
        # pylint: disable=too-many-arguments
        # pylint: disable=super-init-not-called
        if parameter_dict:
            if not isinstance(parameter_dict, dict):
                raise ValueError('parameter_dict is not a dictionary')
            self._vals = parameter_dict
        else:  # if None, read current-law policy parameters
            self._vals = self._params_dict_from_json_file()

        if parameter_dict is None and start_year < Policy.JSON_START_YEAR:
            msg = 'start_year={} < JSON_START_YEAR={}'
            raise ValueError(msg.format(start_year,
                                        Policy.JSON_START_YEAR))

        if inflation_rates:
            if len(inflation_rates) != num_years:
                raise ValueError('len(inflation_rates) != num_years')
            if min(list(inflation_rates.keys())) != start_year:
                raise ValueError('min(inflation_rates.keys()) != start_year')
            self._inflation_rates = [inflation_rates[start_year + i]
                                     for i in range(0, num_years)]
        else:  # if None, read default rates
            self._inflation_rates = [self.__pirates[start_year + i]
                                     for i in range(0, num_years)]

        if wage_growth_rates:
            if len(wage_growth_rates) != num_years:
                raise ValueError('len(wage_growth_rates) != num_years')
            if min(list(wage_growth_rates.keys())) != start_year:
                msg = 'min(wage_growth_rates.keys()) != start_year'
                raise ValueError(msg)
            self._wage_growth_rates = [wage_growth_rates[start_year + i]
                                       for i in range(0, num_years)]
        else:  # if None, read default rates
            self._wage_growth_rates = [self.__wgrates[start_year + i]
                                       for i in range(0, num_years)]

        self.initialize(start_year, num_years)

    def inflation_rates(self):
        """
        Returns list of price inflation rates starting with JSON_START_YEAR.
        """
        return self._inflation_rates

    def wage_growth_rates(self):
        """
        Returns list of wage growth rates starting with JSON_START_YEAR.
        """
        return self._wage_growth_rates

    @staticmethod
    def read_json_reform_file(reform_filename):
        """
        Read reform file, strip //-comments, and return dict based on JSON.
        The reform file is JSON with string policy-parameter primary keys and
           string years as secondary keys.  See tests/test_policy.py for an
           extended example of a commented JSON reform file that can be read
           by this function.
        Returned dictionary has integer years as primary keys and
           string policy-parameters as secondary keys.
        The returned dictionary is suitable as the argument to the
           implement_reform(reform_dict) method (see below).
        """
        # check existence of specified reform file
        if not os.path.isfile(reform_filename):
            msg = 'simtax REFORM file {} could not be found'
            raise ValueError(msg.format(reform_filename))
        # read contents of reform file and remove // comments
        with open(reform_filename, 'r') as reform_file:
            json_with_comments = reform_file.read()
            json_without_comments = re.sub('//.*', '', json_with_comments)
        # convert JSON text into a dictionary with year skeys as strings
        try:
            reform_dict_raw = json.loads(json_without_comments)
        except ValueError:
            msg = 'simtax REFORM file {} contains invalid JSON'
            line = '----------------------------------------------------------'
            txt = ('TO FIND FIRST JSON SYNTAX ERROR,\n'
                   'COPY TEXT BETWEEN LINES AND '
                   'PASTE INTO BOX AT jsonlint.com')
            sys.stderr.write(txt + '\n')
            sys.stderr.write(line + '\n')
            sys.stderr.write(json_without_comments.strip() + '\n')
            sys.stderr.write(line + '\n')
            raise ValueError(msg.format(reform_filename))
        # convert year skey strings to integers and lists into np.arrays
        reform_pkey_param = {}
        for pkey, sdict in reform_dict_raw.items():
            if not isinstance(pkey, six.string_types):
                msg = 'pkey {} in reform is not a string'
                raise ValueError(msg.format(pkey))
            rdict = {}
            for skey, val in sdict.items():
                if not isinstance(skey, six.string_types):
                    msg = 'skey {} in reform is not a string'
                    raise ValueError(msg.format(skey))
                else:
                    year = int(skey)
                rdict[year] = (np.array(val)
                               if isinstance(val, list) else val)
            reform_pkey_param[pkey] = rdict
        # convert reform_pkey_param dictionary to reform_pkey_year dictionary
        return Policy._reform_pkey_year(reform_pkey_param)

    def implement_reform(self, reform):
        """
        Implement multi-year policy reform and leave current_year unchanged.

        Parameters
        ----------
        reform: dictionary of one or more YEAR:MODS pairs
            see Notes to _update function for details on MODS structure, and
            see read_json_reform_file method above for how to specify a
            reform in a JSON file and translate it into a reform dictionary
            suitable for input into this implement_reform method.
        Raises
        ------
        ValueError:
            if reform is not a dictionary.
            if each YEAR in reform is not an integer.
            if minimum YEAR in the YEAR:MODS pairs is less than start_year.
            if minimum YEAR in the YEAR:MODS pairs is less than current_year.
            if maximum YEAR in the YEAR:MODS pairs is greater than end_year.

        Returns
        -------
        nothing: void

        Notes
        -----
        Given a reform dictionary, typical usage of the Policy class
        is as follows::

            policy = Policy()
            policy.implement_reform(reform)

        In the above statements, the Policy() call instantiates a
        policy object (policy) containing current-law policy parameters,
        and the implement_reform(reform) call applies the (possibly
        multi-year) reform specified in reform and then sets the
        current_year to the value of current_year when implement_reform
        was called with parameters set for that pre-call year.

        An example of a multi-year, multi-parameter reform is as follows::

            reform = {
                2015: {
                    '_AMT_thd_MarriedS': [60000]
                },
                2016: {
                    '_EITC_c': [[900, 5000, 8000, 9000]],
                    '_II_em': [7000],
                    '_SS_Earnings_c': [300000]
                },
                2017: {
                    '_AMT_thd_MarriedS': [80000],
                    '_SS_Earnings_c': [500000], '_SS_Earnings_c_cpi': False
                },
                2019: {
                    '_EITC_c': [[1200, 7000, 10000, 12000]],
                    '_II_em': [9000],
                    '_SS_Earnings_c': [700000], '_SS_Earnings_c_cpi': True
                }
            }

        Notice that each of the four YEAR:MODS pairs is specified as
        required by the private _update method, whose documentation
        provides several MODS dictionary examples.
        """
        if not isinstance(reform, dict):
            msg = 'reform passed to implement_reform is not a dictionary'
            ValueError(msg)
        if not reform:
            return  # no reform to implement
        reform_years = sorted(list(reform.keys()))
        for year in reform_years:
            if not isinstance(year, int):
                msg = 'key={} in reform is not an integer calendar year'
                raise ValueError(msg.format(year))
        first_reform_year = min(reform_years)
        if first_reform_year < self.start_year:
            msg = 'reform provision in year={} < start_year={}'
            ValueError(msg.format(first_reform_year, self.start_year))
        if first_reform_year < self.current_year:
            msg = 'reform provision in year={} < current_year={}'
            ValueError(msg.format(first_reform_year, self.current_year))
        last_reform_year = max(reform_years)
        if last_reform_year > self.end_year:
            msg = 'reform provision in year={} > end_year={}'
            ValueError(msg.format(last_reform_year, self.end_year))
        precall_current_year = self.current_year
        for year in reform_years:
            self.set_year(year)
            self._update({year: reform[year]})
        self.set_year(precall_current_year)

    # ----- begin private methods of Policy class -----

    @staticmethod
    def _reform_pkey_year(reform_pkey_param):
        """
        The input reform_pkey_param dictionary has string policy-parameter
           primary keys and integer years as secondary keys.
        Returned dictionary has integer years as primary keys and
           string policy-parameters as secondary keys.
        The returned dictionary is suitable as the argument to the
           implement_reform(reform_dict) method (see above).
        """
        years = set()
        reform_pk_yr = {}
        for param, sdict in reform_pkey_param.items():
            if not isinstance(param, six.string_types):
                msg = 'pkey {} in reform is not a string'
                raise ValueError(msg.format(param))
            elif not isinstance(sdict, dict):
                msg = 'pkey {} value {} is not a dictionary'
                raise ValueError(msg.format(param, sdict))
            for year, val in sdict.items():
                if not isinstance(year, int):
                    msg = 'year skey {} in reform is not an integer'
                    raise ValueError(msg.format(year))
                if year not in years:
                    years.add(year)
                    reform_pk_yr[year] = {}
                reform_pk_yr[year][param] = val
        return reform_pk_yr


# end Policy class
