"""
Ridgid testing script for an initial run of the system
Test cases are order dependent and must be run in the order set by the file
Test Case Format:
name: Name of the test case
method: HTTP method to use (GET or POST supported)
target: The endpoint to target
data: JSON formatted data to send
authorization: The authorization header to send eg. Bearer {token}
response: The expected response to compare with
capture: Any information to be captured by the response used to force matching with the expected results
"""
import requests
import json
import csv
import sys
import os

token = ''
base_url = "http://localhost:8080/" #TODO: Turn into a command line argument

"""Accepts a test case and executes it"""
def run_test_case(test_case):
    global token
    response = None
    test_headers = {}

    #Applys the necessary token for authorization
    if test_case.get('authorization') != '':
        test_headers["Authorization"] = test_case.get('authorization').replace('"$token$"',token)

    #Places empty dictionary in the case no data is sent
    if test_case.get('data') == '':
        test_case['data'] = "{}"

    #Executes the request based on the HTTP method
    if test_case['method'] == 'post':
        response = requests.post(base_url+test_case['target'], json=json.loads(test_case['data']), headers = test_headers).json()
    elif test_case['method'] == 'get':
        response = requests.get(base_url+test_case['target'], json=json.loads(test_case['data']), headers = test_headers).json()
      
    #Express the expected result as a dictionary
    expected_response = json.loads(test_case['response'])

    #TODO: Develop method not dependent on generalizing large portions of the response

    #Capture any tokens set to be captures as defined by the test case
    #And set the expected response to be that token
    if test_case['capture'] == "token":
        token = response['result']['token']
        expected_response['result']['token']=token

    #Cature any information requested to be captured
    elif test_case['capture'] != '':
        response['result'][test_case['capture']]  = '$listing$'

    #Check the pass state of the test case and print the result, returning the value
    passed = (response == expected_response)
    print(test_case['name']+': {0}'.format(passed))
    return passed,expected_response,response


if __name__ == "__main__":   
    passed_tests = num_test_cases = 0
    failed_cases = []

    #Capture the test file based on command line arguments which defaults to test_cases.csv in the current folder
    test_file = '/'+sys.argv[1] if len(sys.argv) > 1 else '/test_cases.csv'

    #Opens the test case file
    with open(os.getcwd()+test_file, newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=',', quotechar="'")

        #Loop through each test case and store the pass state, expected result and the received result
        for test_case in reader:
            passed,expected,recieved = run_test_case(test_case)

            #Stores the results
            num_test_cases+=1
            passed_tests+=passed
            if not passed: 
                failed_cases.append({'name':test_case['name'],'expected':expected,'recieved':recieved})

    #Displays the results of the test cases ran
    print("Number of cases: {0}".format(num_test_cases))
    print("Passed cases: {0}".format(passed_tests))
    print("Failed cases:")
    print(failed_cases)