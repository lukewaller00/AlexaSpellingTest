import logging
import os
import boto3
from botocore.exceptions import ClientError
from ask_sdk_core.handler_input import HandlerInput

from ask_sdk_dynamodb.adapter import DynamoDbAdapter

ddb_region = os.environ.get('DYNAMODB_PERSISTENCE_REGION')
ddb_table_name = os.environ.get('DYNAMODB_PERSISTENCE_TABLE_NAME')

ddb_resource = boto3.resource('dynamodb', region_name=ddb_region)
dynamodb_adapter = DynamoDbAdapter(table_name=ddb_table_name, create_table=False, dynamodb_resource=ddb_resource)



def create_presigned_url(object_name):
    """Generate a presigned URL to share an S3 object with a capped expiration of 60 seconds

    :param object_name: string
    :return: Presigned URL as string. If error, returns None.
    """
    s3_client = boto3.client('s3',
                             region_name=os.environ.get('S3_PERSISTENCE_REGION'),
                             config=boto3.session.Config(signature_version='s3v4',s3={'addressing_style': 'path'}))
    try:
        bucket_name = os.environ.get('S3_PERSISTENCE_BUCKET')
        response = s3_client.generate_presigned_url('get_object',
                                                    Params={'Bucket': bucket_name,
                                                            'Key': object_name},
                                                    ExpiresIn=60*1)
    except ClientError as e:
        logging.error(e)
        return None

    # The response contains the presigned URL
    return response

def get_word_to_practise(handler_input):
    #handler_input -> String
    session_attr = handler_input.attributes_manager.session_attributes
    currentWordList = session_attr["words"]
    counter = session_attr["nextWordIndex"]
    if len(currentWordList) == 0:
        return "0"
    elif counter < len(currentWordList)-1:
        currentWord = currentWordList[counter]
        counter += 1
        session_attr["nextWordIndex"] = counter
        return currentWord
    elif counter == len(currentWordList)-1:
        currentWord = currentWordList[counter]
        counter+=1
        session_attr["nextWordIndex"] = counter
        return currentWord
    else:
        return "1"

def create_word_report(handler_input):
    #handler_input -> dict
    session_attr = handler_input.attributes_manager.session_attributes
    currentWordList = session_attr["words"]
    report = session_attr["wordReport"]
    for word in currentWordList:
        report[word] = 0
    return report

def sortReport(report):
    #dict -> list
    """ This helper function will take a given wordReport and return a list of tuple containing the individual word and the incorrect attempts. """
    sortedReport = sorted(report.items(),key = lambda t: t[1],reverse=True)
    #print(sortedReport)
    return sortedReport

def get_ordinal_indicator(handler_input,counter):
    #handler_input, Int -> String
    """Return st, nd, rd, th ordinal indicators according to counter."""
    session_attr = handler_input.attributes_manager.session_attributes
    if len(session_attr["words"]) -1  == counter:
        return "last"
    counter +=1
    if counter == 1:
        return "1st"
    elif counter == 2:
        return "2nd"
    elif counter == 3:
        return "3rd"
    elif counter >20:
        return "next"
    else:
        return "{}th".format(str(counter))

def get_spelling_for_word(word):
    # String -> String
    #use ssml tag <break> to add pause after each letter
    spelling = "<break time ='0.5s'></break>".join(word)
    #spelling = '.'.join(word)
    return spelling

def get_phoenetics_for_letter(letter):
    # String -> String
    """Helper function to get phonetic sound of individual letter in the word."""
    phonemes =''
    phonemes = letterPhonemeDict[letter]
    return phonemes


def get_phonetic_spelling(word):
    #String -> String
    """ This function will take a given word and construct a phonetic spelling which is the combination of phonetic sound of each letter in the word."""
    spelling = ""
    for letter in word:
        spelling = spelling + get_phoenetics_for_letter(letter) +" <break time ='0.3s'></break>" 
    return spelling



#This Python Dictionary holds the phonics sound of each letter.
letterPhonemeDict = {
    "a": "ah",
    "b": "buh",
    "c": "cuh",
    "d": "duh",
    "e": "eh",
    "f": "fuh",
    "g": "guh",
    "h": "huh",
    "i": "eeh",
    "j": "jawh",
    "k": "cuh",
    "l": "ul",
    "m": "mmm",
    "n": "uhn",
    "o": "ohh",
    "p": "pppuh",
    "q": "koo",
    "r": "err",
    "s": "sshh",
    "t": "ttuh",
    "u": "uh",
    "v": "vvvooh",
    "w": "wuh",
    "x": "kusssshhh",
    "y": "yuh",
    "z": "zzizz"
}
