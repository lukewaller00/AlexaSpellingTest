import logging
import ask_sdk_core.utils as ask_utils

import utils

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput

from ask_sdk_model import Response

import os
import boto3

from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_dynamodb.adapter import DynamoDbAdapter

ddb_region = os.environ.get('DYNAMODB_PERSISTENCE_REGION')
ddb_table_name = os.environ.get('DYNAMODB_PERSISTENCE_TABLE_NAME')

ddb_resource = boto3.resource('dynamodb', region_name=ddb_region)
dynamodb_adapter = DynamoDbAdapter(table_name=ddb_table_name, create_table=False, dynamodb_resource=ddb_resource)


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class LaunchRequestHandler(AbstractRequestHandler):
    """ Handler for Skill Launch.
    @Requires skill name to be invoked.
    
    At the launch of the Skill, initialise some session attributes to manage
    and track the flow of the program.
    
    session_attr contains all the attribute for a given session
    
    Session attributes
    ------------------
    words: str array 
        List of words added by the parent for practise. Empty if nothing has been added yet.
    nextWordIndex : int 
        Index used to return a word while iterating from the list of words
    state: str 
        A string that keeps track of the state of program, e.g. 'ADDUSER', 'TEST'
    numOfWords:
        Tracks the number of words in the users current word List
    correctAnswers:
        Tracks the number of correct answers a user gives in a quiz
    wordReport:
        Stores all words and how many times the user has gotten the wrong
    testAttempts:
        Tracks the number of times a user has begun a test
    
    persistent_attr contains all the attributes that is to be saved to the database
    
    Persistent attributes
    ---------------------
    words: str array 
        List of words that is already in the database. Empty if no words have been added.
    userName: str
        Name of the user who is using the skill. Used to personalise the experience while using the skill.

    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Welcome to spelling practice, you can update your list or begin a test"
        
        #initialising session attributes and persistent attributes.
        session_attr = handler_input.attributes_manager.session_attributes
        persistent_attr = handler_input.attributes_manager.persistent_attributes
        
        session_attr["nextWordIndex"] = 0
        session_attr["words"] = []
        session_attr["numOfWords"] = 0
        session_attr["correctAnswers"] = 0
        session_attr["wordReport"] = {}
        session_attr["testAttempts"] = 0
        session_attr["pronounciation"] = "phonetic"
        
        #No words in the database
        if persistent_attr.get("words") is None: 
            #assign an empty list for the words to be saved
            persistent_attr["words"] = []
        else:
            #Get the words from the database for the session
            session_attr["words"] = persistent_attr["words"]
            session_attr["numOfWords"] = len(session_attr.get("words"))
        
        #check for test attempt number
        if persistent_attr.get("testAttempts") is None:
            persistent_attr["testAttempts"] = session_attr["testAttempts"]
        else:
            session_attr["testAttempts"] = persistent_attr["testAttempts"]
            
        
        #Checks for existing Word Report
        if persistent_attr.get("wordReport") is None:
            persistent_attr["wordReport"] = {}
        else:
            session_attr["wordReport"] = persistent_attr["wordReport"]
            
        #No users found in the database
        if persistent_attr.get("userName") is None:
            #Change the state of the program to add user
            session_attr["state"] = "ADDUSER"
            speak_output = "Have we met before? Please tell me your name to continue."
            return(
                handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )
        #User present in the database
        else:
            speak_output = "Welcome to Spelling Practice " +persistent_attr["userName"] + ". You can update your list or begin a test"
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

class GetUsernameIntentHandler(AbstractRequestHandler):
    """Handler to add the username to the database.
    
    @Requires session to be in ADDUSER state and a name is uttered by the user.
    userName: str
        Name of the user. Obtained from the slot named "userName" in the request body.
    persistent_attr["userName"]: str
        Assigned the previously obtained userName to save to the database.
        
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        session_attr = handler_input.attributes_manager.session_attributes
        return (
            ask_utils.is_intent_name("GetUsernameIntent")(handler_input)
            and
            (session_attr.get("state") == "ADDUSER")
        )

    def handle(self, handler_input):
        
        persistent_attr = handler_input.attributes_manager.persistent_attributes
        userName = ask_utils.request_util.get_slot_value(handler_input,"userName")
        persistent_attr["userName"] = userName
        speak_output = "Hello " + userName + ". Welcome to Alexa Spelling Test Helper. You can say update my list or begin  test."
        handler_input.attributes_manager.save_persistent_attributes()

        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )

class BeginQuizIntentHandler(AbstractRequestHandler):
    """Handler to launch the quiz/test for the child.
    @Requires user asks to begin test
    
    get_word_to_practise(handler_input) -> str:
        Helper function that returns a string containing a word to practise
        
    session_attr["state"] set to TEST to run a test during the session
    session_attr["testAttempts"] to keep track of number of times the child runs the test
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("BeginQuizIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        session_attr = handler_input.attributes_manager.session_attributes
        persistent_attr = handler_input.attributes_manager.persistent_attributes
        session_attr["nextWordIndex"] = 0
        session_attr["testAttempts"] += 1
        persistent_attr["testAttempts"] = session_attr["testAttempts"]
        handler_input.attributes_manager.save_persistent_attributes()
        if len(session_attr["words"])  == 0:
            speak_output = "Please add words to your spelling list to begin a test"
        else:
            session_attr["state"] = "TEST"
            word_to_practise = utils.get_word_to_practise(handler_input)
            speak_output = "Your test will now begin. " + "Your first word is:<break time='0.3s'></break> " + word_to_practise
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

class TellWordIntentHandler(AbstractRequestHandler):
    """
    Handler for asking Alexa to read out words one at a time.
    
    @Requires session to be in TEST state and user asks for next words.
    
    get_word_to_practise(handler_input) -> str:
        Helper function that returns a string containing a word to practise
        
    """
    def can_handle(self, handler_input):
        session_attr = handler_input.attributes_manager.session_attributes
        return (ask_utils.is_intent_name("TellWordIntent")(handler_input)
            and 
            (session_attr.get("state") == "TEST")
        )
    
    def handle(self, handler_input):
        session_attr = handler_input.attributes_manager.session_attributes
        counter = session_attr["nextWordIndex"]
        currentWord = utils.get_word_to_practise(handler_input)
        if currentWord == "0":
            speak_output = "You haven't added any words yet. Say update my spelling list to add words to your spelling list."
        elif currentWord == "1":
            speak_output = "You have completed your spelling test! You can say 'begin checking' to check your spellings."
        elif currentWord != "0" or currentWord != "1":
            speak_output = "Your {} word is: {}".format(utils.get_ordinal_indicator(handler_input,counter), currentWord)
        
        return(
            handler_input.response_builder
            .speak(speak_output)
            .ask(speak_output)
            .response
            )

class BeginMarkingIntentHandler(AbstractRequestHandler):
    """ Hanlder for the child's intent to check the spelling of the words they just practised.
    
    session_attr["state"] set to MARKING to check answers/spellings during the session
    session_attr["wordReport"] to keep track of number of words the child got incorrect
    session_attr["pronounciation"] set by default to 'phonetics' to get the phonetic spelling. 
    
    utils.get_spelling_for_word(word_to_practise) -> str:
        Helper function that returns the spelling of the given word as individual letters.
    
      utils.get_phonetic_spelling(word_to_practise) -> str:
        Helper function that returns the phonetic spelling of the given word.
    """
    def can_handle(self, handler_input):
        session_attr = handler_input.attributes_manager.session_attributes
        return (ask_utils.is_intent_name("BeginMarkingIntent")(handler_input)
           # and 
           # (session_attr.get("state") == "MARKING")
        )
    
    def handle(self, handler_input):
        session_attr = handler_input.attributes_manager.session_attributes
        persistent_attr = handler_input.attributes_manager.persistent_attributes
        report = session_attr["wordReport"]
        #checks if report is empty and initialises it
        if not bool(report):
            report = utils.create_word_report(handler_input)
        session_attr["nextWordIndex"] = 0
        if len(session_attr["words"])  == 0:
            speak_output = "Please add words to your spelling list to begin spell-checking"
        else:
            session_attr["state"] = "MARKING"
            word_to_practise = utils.get_word_to_practise(handler_input)
            if session_attr["pronounciation"] == "letters":
                speak_output = "Spell-Checker will now begin. " + "Your first word was " + word_to_practise + ". The spelling is: " + utils.get_spelling_for_word(word_to_practise) + ".<break time='0.5s'></break> Did you get that right?"
            else:
                speak_output = "Spell-Checker will now begin. " + "Your first word was " + word_to_practise + ". The spelling is: " + utils.get_phonetic_spelling(word_to_practise) + ".<break time='0.5s'></break> Did you get that right?"
        return(
            handler_input.response_builder
            .speak(speak_output)
            .ask(speak_output)
            .response
            )


class TellAnswerIntentHandler(AbstractRequestHandler):
    """
    Handler for asking Alexa to read out the word first and their spelling one at a time.
    
    @Requires session to be in MARKING state and user asks for next answer/spelling.
    
    get_word_to_practise(handler_input) -> str:
        Helper function that returns a string containing a word to practise
        
    """
    def can_handle(self, handler_input):
        session_attr = handler_input.attributes_manager.session_attributes
        return (ask_utils.is_intent_name("TellAnswerIntent")(handler_input)
            and 
            (session_attr.get("state") == "MARKING")
        )
    #This handle function is the previous function where it returned a spelling of the word with the pause between each letters.
    def handle(self, handler_input):
        session_attr = handler_input.attributes_manager.session_attributes
        pronounciation = session_attr.get("pronounciation")
        speak_output = pronounciation
        #if user wants the words spelled out as letter
        if pronounciation == "letters":
            session_attr = handler_input.attributes_manager.session_attributes
            counter = session_attr["nextWordIndex"]
            currentWord = utils.get_word_to_practise(handler_input)
            if currentWord == "0":
                speak_output = "I'm sorry but it seems that there are no words for you to practise this week."
            elif currentWord == "1":
                speak_output = "Spell-Checker Completed. You can close this program now."    
            elif currentWord != "0" or currentWord != "1":
                #the prosody tag will let us set the speed in which Alexa spells out each letter 
                #use it similarly for phonemes in the future
                speak_output = "Your {} word was {}".format(utils.get_ordinal_indicator(handler_input,counter), currentWord) + ". It is spelt as: " + utils.get_spelling_for_word(currentWord) + ".<break time='0.5s'></break> Did you get that right?"
        #default phonetic spelling
        if pronounciation == "phonetic":
            session_attr = handler_input.attributes_manager.session_attributes
            counter = session_attr["nextWordIndex"]
            currentWord = utils.get_word_to_practise(handler_input)
            if currentWord == "0":
                speak_output = "I'm sorry but it seems that there are no words for you to practise this week."
            elif currentWord == "1":
                speak_output = "That's all the words you needed to practise today. You can close this program now."    
            elif currentWord != "0" or currentWord != "1":
                speak_output = "Your {} word was {}".format(utils.get_ordinal_indicator(handler_input,counter), currentWord) + ". It is spelt as: " + utils.get_phonetic_spelling(currentWord) + ".<break time='0.5s'></break> Did you get that right?"
                #speak_output = "Your {} word was {}".format(utils.get_ordinal_indicator(handler_input,counter), currentWord) + ". It is spelt as: " + utils.get_spelling_for_word(currentWord) + ".<break time='0.5s'></break> Did you get that right?"
        return(handler_input.response_builder
        .speak(speak_output)
        .ask(speak_output)
        .response
        )

class ClearSpellingListIntentHandler(AbstractRequestHandler):
    """Handler to clear the user's current word list
    
    persistent_attr["words"] are the current words set for the child to practise
    session_attr["words"] contains words from the database as well as any words the user might have added in the current session that is not\
        saved to the database yet.
    
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("ClearSpellingListIntent")(handler_input)

    def handle(self, handler_input):
        session_attr = handler_input.attributes_manager.session_attributes
        persistent_attr = handler_input.attributes_manager.persistent_attributes
        session_attr["words"] = []
        persistent_attr["words"] = session_attr["words"]
        #save empty word list to the database
        handler_input.attributes_manager.save_persistent_attributes()
        speak_output = "Ok. I have cleared all the words from your spelling list. You can make a new list by saying 'create a new spelling list'."
        return (
            handler_input.response_builder.speak(speak_output)
                .response
        )

class ConfirmWordIntentHandler(AbstractRequestHandler):
    """Handler to confirm if the child got a particular word right/wrong.
    
    @Requires child to confirm if they got the word right/wrong by saying yes or no
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("ConfirmWordIntent")(handler_input)

    def handle(self, handler_input):
        session_attr = handler_input.attributes_manager.session_attributes
        persistent_attr = handler_input.attributes_manager.persistent_attributes
        answer = ask_utils.request_util.get_slot_value(handler_input,"yesNo")
        report = session_attr["wordReport"]
        currentWord = session_attr["words"][session_attr["nextWordIndex"]-1]
        if answer == "yes":
            session_attr["correctAnswers"] += 1
            if session_attr["nextWordIndex"] == len(session_attr["words"]):
                speak_output = "Well done! Spell-Checking Complete"
            else:
                speak_output = "Well done! You can say 'next one' to hear the spelling of your next word."   
        else:
            #if they got it wrong, increase the count for the word to denote they got it wrong.
            report[currentWord] += 1
            if session_attr["nextWordIndex"] == len(session_attr["words"]):
                speak_output = "Unlucky! Spell-Checking Complete"
            else:
                speak_output = "Unlucky! You can say 'next one' to hear the spelling of your next word."
        session_attr["wordReport"] = report
        persistent_attr["wordReport"] = session_attr["wordReport"]
        handler_input.attributes_manager.save_persistent_attributes()
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

class ChildPractiseReportIntentHandler(AbstractRequestHandler):
    """Handler to show parents how well their child practised the set words.
    
    @Requires parent to ask alexa to show the child's report
    
     session_attr["wordReport"] is a dictionary containing the the word and the corresponding number denotes the number of times the child got it wrong.
     session_attr["testAttempts"] is the number of times the child attemepted the test.
    utils.sortReport(report) -> dict:
        It takes wordReport python dictionary and returns a sorted python dictionary
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("ChildPractiseReportIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        session_attr = handler_input.attributes_manager.session_attributes
        persistent_attr = handler_input.attributes_manager.persistent_attributes
        name = persistent_attr["userName"]
        report = session_attr["wordReport"]
        #sorts dictionary of report with most incorrect words first
        #sortedReport = sorted(report.items(), key=lambda x: x[1], reverse=True)
        sortedReport = utils.sortReport(report)
        #speak_output = name + " has currently attempted the test " + str(session_attr["testAttempts"]) + " times, and their most incorrect words are, " + str(sortedReport)
        speak_output =  name + " has currently attempted the test " + str(session_attr["testAttempts"]) + " times."
        for key, value in sortedReport:
            if value != 0:
                speak_output += " They got the word " + key + " wrong " + str(value) + " times. "

        # print resulting string
        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )
    
class AddSpellingIntentHandler(AbstractRequestHandler):
    """Handler to update the list of words containing the spellings to be practised.
    
    @Requires user to ask alexa to create a new list for spellings or update the existing list.
    words: str 
        Contains a string of words added by the user. The value is obtained from the slot named 'words' in 
        the AddSpellingIntent of the interaction model. Can contain a single word or multiple words separated
        by a space.Deployment
    
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AddSpellingIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        session_attr = handler_input.attributes_manager.session_attributes
        persistent_attr = handler_input.attributes_manager.persistent_attributes
        
        #split all the words in the string and make a list 
        slot_words = ask_utils.request_util.get_slot_value(handler_input,"words").split()
        
        session_attr["words"] += slot_words
        persistent_attr["words"] = session_attr["words"]
        #reset the number of test attempts after new words are added to the list
        session_attr["testAttempts"] = 0
        persistent_attr["testAttempts"] = session_attr["testAttempts"]
        #save the words to the database
        handler_input.attributes_manager.save_persistent_attributes()
        #creates new report to reset incorrect answers for words
        report = utils.create_word_report(handler_input)
        session_attr["wordReport"] = report
        persistent_attr["wordReport"] = session_attr["wordReport"]
        #new report is saved persistently
        handler_input.attributes_manager.save_persistent_attributes()
        speak_output = "Ok. I have added the word."   
        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )

class ChangeToPhoneticsIntentHandler(AbstractRequestHandler):
    """Handler for changing answers to phonetics."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("ChangeToPhoneticsIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        session_attr = handler_input.attributes_manager.session_attributes
        session_attr["pronounciation"] = "phonetics"
        speak_output = "Answers will be told in phonetics"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

class ChangeToLettersIntentHandler(AbstractRequestHandler):
    """Handler for changing answers to Letters."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("ChangeToLettersIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        session_attr = handler_input.attributes_manager.session_attributes
        session_attr["pronounciation"] = "letters"
        speak_output = "Answers will be told in letters"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "You can say hello to me! How can I help?"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Goodbye!"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )


class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        # Any cleanup logic goes here.
        return handler_input.response_builder.response


class IntentReflectorHandler(AbstractRequestHandler):
    """The intent reflector is used for interaction model testing and debugging.
    It will simply repeat the intent the user said. You can create custom handlers
    for your intents by defining them above, then also adding them to the request
    handler chain below.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        intent_name = ask_utils.get_intent_name(handler_input)
        speak_output = "You just triggered " + intent_name + "."

        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handling to capture any syntax or routing errors. If you receive an error
    stating the request handler chain is not found, you have not implemented a handler for
    the intent being invoked or included it in the skill builder below.
    """
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)

        speak_output = "Sorry, I had trouble doing what you asked. Please try again."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.


sb = CustomSkillBuilder(persistence_adapter = dynamodb_adapter)

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(BeginQuizIntentHandler())
sb.add_request_handler(GetUsernameIntentHandler())
sb.add_request_handler(AddSpellingIntentHandler())
sb.add_request_handler(ChildPractiseReportIntentHandler())
sb.add_request_handler(BeginMarkingIntentHandler())
sb.add_request_handler(ConfirmWordIntentHandler())
sb.add_request_handler(ChangeToLettersIntentHandler())
sb.add_request_handler(ChangeToPhoneticsIntentHandler())
sb.add_request_handler(ClearSpellingListIntentHandler())
sb.add_request_handler(TellWordIntentHandler())
sb.add_request_handler(TellAnswerIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(IntentReflectorHandler()) # make sure IntentReflectorHandler is last so it doesn't override your custom intent handlers

sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()
