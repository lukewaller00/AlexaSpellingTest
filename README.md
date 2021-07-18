# Scrum 02

CO2201 Semester 2 Group 02 Repository

## How to get up and running:
1. Go to https://developer.amazon.com/alexa/console/ask and create an account
2. From the developer console, create a new skill and give your skill a name of your choosing.  Then select the default language as Engligh(UK) and select a Custom model as the model for your skill and select Alexa Hosted(Python) as the method for your skill's backend resources.
3. On the next screen, select "Start From Scratch" and click on "Continue with template".
4. Open the JSON Editor founnd inside the Interaction Model on the left side nav bar on the developer console and replace the code in the editor with the contents of en-GB.json file in this repo. This json file contains all the intents and sample utterances that we use for this skill. Build the model after saving it.
5. Open the code editor by clicking on 'Code' tab next to your 'Build' tab and replace all files with those in the [Lambda Folder](https://campus.cs.le.ac.uk/gitlab/jbh13/scrum-02/-/tree/master/lambda) of this repository
6. Save and Deploy your skill.
7. Use the Test Tab to run the skill. Make sure to switch the skill testing to "Development"
8. To view DynamoDB Attributes open DynamoDB Database on the Code Tab

## Application Flow:
![Image of Application Flowchart](https://github.com/lukewaller00/AlexaSpellingTest/blob/main/flowchart.png)

