#!/usr/bin/env python2

import cmath
import csv
import os
import os.path
import math
import re
import subprocess
import sys

CMD = './mdl'
BASE = 'test/compat'
EXTS = ['xmile']  #, 'stmx', 'itmx', 'STMX', 'ITMX', 'mdl', 'MDL']

# from rainbow
def make_reporter(verbosity, quiet, filelike):
    if not quiet:
        def report(level, msg, *args):
            if level <= verbosity:
                if len(args):
                    filelike.write(msg % args + '\n')
                else:
                    filelike.write('%s\n' % (msg,))
    else:
        def report(level, msg, *args): pass
    return report

ERROR = 0
WARN = 1
INFO = 2
DEBUG = 3
log = make_reporter(DEBUG, False, sys.stderr)

def isclose(a,
            b,
            rel_tol=1e-9,
            abs_tol=0.0,
            method='weak'):
    """
    returns True if a is close in value to b. False otherwise
    :param a: one of the values to be tested
    :param b: the other value to be tested
    :param rel_tol=1e-8: The relative tolerance -- the amount of error
                         allowed, relative to the magnitude of the input
                         values.
    :param abs_tol=0.0: The minimum absolute tolerance level -- useful for
                        comparisons to zero.
    :param method: The method to use. options are:
                  "asymmetric" : the b value is used for scaling the tolerance
                  "strong" : The tolerance is scaled by the smaller of
                             the two values
                  "weak" : The tolerance is scaled by the larger of
                           the two values
                  "average" : The tolerance is scaled by the average of
                              the two values.
    NOTES:
    -inf, inf and NaN behave similar to the IEEE 754 standard. That
    -is, NaN is not close to anything, even itself. inf and -inf are
    -only close to themselves.
    Complex values are compared based on their absolute value.
    The function can be used with Decimal types, if the tolerance(s) are
    specified as Decimals::
      isclose(a, b, rel_tol=Decimal('1e-9'))
    See PEP-0485 for a detailed description

    Copyright: Christopher H. Barker
    License: Apache License 2.0 http://opensource.org/licenses/apache2.0.php
    """
    if method not in ("asymmetric", "strong", "weak", "average"):
        raise ValueError('method must be one of: "asymmetric",'
                         ' "strong", "weak", "average"')

    if rel_tol < 0.0 or abs_tol < 0.0:
        raise ValueError('error tolerances must be non-negative')

    if a == b:  # short-circuit exact equality
        return True
    # use cmath so it will work with complex or float
    if cmath.isinf(a) or cmath.isinf(b):
        # This includes the case of two infinities of opposite sign, or
        # one infinity and one finite number. Two infinities of opposite sign
        # would otherwise have an infinite relative tolerance.
        return False
    diff = abs(b - a)
    if method == "asymmetric":
        return (diff <= abs(rel_tol * b)) or (diff <= abs_tol)
    elif method == "strong":
        return (((diff <= abs(rel_tol * b)) and
                 (diff <= abs(rel_tol * a))) or
                (diff <= abs_tol))
    elif method == "weak":
        return (((diff <= abs(rel_tol * b)) or
                 (diff <= abs(rel_tol * a))) or
                (diff <= abs_tol))
    elif method == "average":
        return ((diff <= abs(rel_tol * (a + b) / 2) or
                (diff <= abs_tol)))
    else:
        raise ValueError('method must be one of:'
                         ' "asymmetric", "strong", "weak", "average"')

def run_cmd(cmd):
    '''
    Runs a shell command, waits for it to complete, and returns stdout.
    '''
    call = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    out, err = call.communicate()
    return (call.returncode, out, err)

def slurp(file_name):
    with open(file_name, 'r') as f:
        return f.read().strip()

def load_csv(f, delimiter=','):
    result = []
    reader = csv.reader(f, delimiter=delimiter)
    header = reader.next()
    for i in range(len(header)):
        result.append([header[i]])
    for row in reader:
        for i in range(len(row)):
            result[i].append(row[i])
    series = {}
    for i in range(len(result)):
        series[result[i][0]] = result[i][1:]
    return series

def read_data(path):
    with open(path, 'r') as f:
        return load_csv(f.read().lower().split('\n'))

NAME_RE = re.compile('\s+')

def e_name(n):
    return NAME_RE.sub('_', n)

def compare(reference, simulated):
    time = reference['time']
    steps = len(time)
    err = False
    for i in range(steps):
        for ref_n, series in reference.items():
            n = e_name(ref_n)
            if len(reference[ref_n]) != len(simulated[n]):
                log(ERROR, 'len mismatch for %s (%d vs %d)',
                    n, len(reference[ref_n]), len(simulated[n]))
                err = True
                break
            ref = series[i]
            sim = simulated[n][i]
            if float(ref) == float(sim):
                continue
            if '.' in ref and '.' in sim and len(ref) != len(sim):
                ref_dec = ref.split('.')[1]
                sim_dec = sim.split('.')[1]
                decimals = min(len(ref_dec), len(sim_dec))
                ref = round(float(ref), decimals)
                sim = round(float(sim), decimals)
            if not isclose(ref, sim):
                log(ERROR, 'time %s mismatch in %s (%s != %s)', time[i], n, ref, sim)
                err = True

def main():
    for model in os.listdir(BASE):
        for mpath in [os.path.join(BASE, model, 'model.' + ext) for ext in EXTS]:
            if not os.access(mpath, os.R_OK):
                continue
            log(DEBUG, 'testing %s', model)
            err, mdata, err_out = run_cmd('%s %s' % (CMD, mpath))
            if err:
                log(ERROR, '%s failed: %s', CMD, err_out)
                break
            simulated = load_csv(mdata.lower().split('\n'), '\t')
            dpath = os.path.join(BASE, model, 'data.csv')
            reference = read_data(dpath)
            compare(reference, simulated)
            break
if __name__ == '__main__':
    exit(main())
