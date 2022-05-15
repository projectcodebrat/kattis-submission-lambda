import json
import boto3
from botocore.errorfactory import ClientError
import requests

_LOGIN_URL = 'https://open.kattis.com/login'
_SUBMIT_URL = 'https://open.kattis.com/submit'
_SUBMISSIONS_URL = 'https://open.kattis.com/submissions'
_S3_BUCKET_NAME = 'codebrat-kattis-code'
_HEADERS = {'User-Agent': 'kattis-cli-submit'}

S3_CLIENT = boto3.client ('s3')

def lambda_handler(event, context):
    username = event['username']
    problem_id = event['problem_id']
    
    # ============== LOGIN ================================================================
    object_key = "{}/kattisrc_json.txt".format(username)
    
    # check if the user has kattis login-info stored in S3
    try:
        S3_CLIENT.head_object(Bucket=_S3_BUCKET_NAME, Key=object_key);
    except ClientError:
        # kattis login info not in user's CodeBrat account
        print('kattis login info not found')
        return None
    
    # get user's login-info for kattis
    file_content = S3_CLIENT.get_object(Bucket=_S3_BUCKET_NAME, Key=object_key)["Body"].read().decode('utf-8')
    account_details = json.loads(file_content)
    kattis_username = account_details['username']
    kattis_password = account_details['password']
    
    login_args = {'user': kattis_username, 'password': kattis_password, 'script': 'true'}
    
    try:
        login_reply = requests.post(_LOGIN_URL, data=login_args, headers=_HEADERS)
    except requests.exceptions.RequestException as err:
        print('Login connection failed:', err)
        sys.exit(1)
        
    # verify that login was successful
    if not login_reply.status_code == 200:
        print('Login failed.')
        if login_reply.status_code == 403:
            print('Incorrect username or password/token (403)')
        elif login_reply.status_code == 404:
            print('Incorrect login URL (404)')
        else:
            print('Status code:', login_reply.status_code)
        sys.exit(1)
        
    print(login_reply.status_code)
    
    # ============== SUBMISSION ================================================================
    # HARDCODED FOR NOW
    language = 'Java'
    files = []
    mainclass = 'Main'
    tag = ''
    result_reply = submit(
                kattis_username,
                problem_id,
                login_reply.cookies,
                language,
                files,
                mainclass,
                tag)
                
    print(result_reply.status_code)

def submit(kattis_username, problem_id, cookies, language, files, mainclass='', tag=''):
    """
    Make a submission.

    The url_opener argument is an OpenerDirector object to use (as
    returned by the login() function)

    Returns the requests.Result from the submission
    """

    data = {'submit': 'true',
            'submit_ctr': 2,
            'language': language,
            'mainclass': mainclass,
            'problem': problem_id,
            'tag': tag,
            'script': 'true'}

    sub_files = []
    # for f in files:
    #     with open(f) as sub_file:
    #         sub_files.append(('sub_file[]',
    #                           (os.path.basename(f),
    #                           sub_file.read(),
    #                           'application/octet-stream')))
    
    object_key = '{}/{}/Main.java'.format(kattis_username, problem_id)
    file = S3_CLIENT.get_object(Bucket=_S3_BUCKET_NAME, Key=object_key)["Body"].read()
    sub_files.append(('sub_file[]',
        ('Main.java', file,'application/octet-stream')
    ))

    return requests.post(_SUBMIT_URL, data=data, files=sub_files, cookies=cookies, headers=_HEADERS)