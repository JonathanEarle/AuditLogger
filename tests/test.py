"""Ridgid testing script for an initial run of the system"""
import requests
import json
import csv
import os

token = ''
base_url = "http://localhost:8080/"

def run_test_case(test_case):
    global token
    response = None
    test_headers = {}

    if test_case.get('authorization') != '':
        test_headers["Authorization"] = test_case.get('authorization').replace('"$token$"',token)

    if test_case.get('data') == '':
        test_case['data'] = "{}"

    if test_case['method'] == 'post':
        response = requests.post(base_url+test_case['target'], json=json.loads(test_case['data']), headers = test_headers).json()
    elif test_case['method'] == 'get':
        response = requests.get(base_url+test_case['target'], json=json.loads(test_case['data']), headers = test_headers).json()
      
    
    expected_response = json.loads(test_case['response'])

    if test_case['capture'] == "token":
        token = response['result']['token']
        expected_response['result']['token']=token

    elif test_case['capture'] != '':
        response['result'][test_case['capture']]  = '$listing$'

    passed = (response == expected_response)
    print(test_case['name']+': {0}'.format(passed))
    return passed,expected_response,response


passed_tests = num_test_cases = 0
failed_cases = []

with open(os.getcwd()+'/test_cases.csv', newline='') as csvfile:
    reader = csv.DictReader(csvfile, delimiter=',', quotechar="'")
    for test_case in reader:
        passed,expected,recieved = run_test_case(test_case)

        num_test_cases+=1
        passed_tests+=passed
        if not passed: 
            failed_cases.append({'name':test_case['name'],'expected':expected,'recieved':recieved})

print("Number of cases: {0}".format(num_test_cases))
print("Passed cases: {0}".format(passed_tests))
print("Failed cases:")
print(failed_cases)