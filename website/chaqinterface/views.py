from django.shortcuts import render_to_response
from django.template import RequestContext
from chaqinterface.models import Conversation
from django.contrib.auth.models import User
import marshal
import os.path

from PyAIML import aiml

# Create your views here.
def index(request):
  return render_to_response('interface/index.html', {}, context_instance=RequestContext(request))


def logs(request):
  conversation_log = Conversation.objects.all().order_by('-timestamp')[:5]
  
  return render_to_response(
    'interface/log.html',
    {
      'conversation_log': conversation_log,
    }
  )

def ask(request):
  
  notice_message = ''

  # Check if a question exists
  if 'question' in request.POST:
    question = request.POST['question']
    status = 'OK'
  else:
    question = ''
    notice_message = 'You did not ask a question ...'
    status = 'ERROR'

  # load pyaiml kernel
  k = aiml.Kernel()

  # load session data if it exists for username
  if os.path.isfile("session_data/username.ses"):
    sessionFile = file("session_data/username.ses", "rb")
    session = marshal.load(sessionFile)
    sessionFile.close()
    for pred,value in session.items():
        k.setPredicate(pred, value, "username")


  # Enabling Verbose mode, to help track down problems
  k.verbose(True)
  # Set the bot's name
  k.setBotPredicate("name","Chaq")

  brainLoaded = False
  forceReload = False
  while not brainLoaded:
    if forceReload:
      k.bootstrap(learnFiles="PyAIML/std-startup.xml", commands="load aiml b")
      brainLoaded = True
      k.saveBrain("PyAIML/standard.brn")
    else:
      try:
        k.bootstrap(brainFile = "PyAIML/standard.brn")
        brainLoaded = True
      except:
        forceReload = True
  
  # send the question to pyaiml and fetch the response
  answer = k.respond(question, "username")

  # save session data to disk for username
  # this should be done every so often, or at logout, etc
  session = k.getSessionData("username")
  sessionFile = file("session_data/username.ses", "wb")
  marshal.dump(session, sessionFile)
  sessionFile.close()

  # close kernel

  print "Session file written to disk\n"

  debug_session_file(session)

  # insert question/answer into user's logs
  # conversation = new Conversation
  # conversation.question = request.POST['question']
  # conversation.answer   = response

  conversation = {
    'status'  : status,
    'question': question,
    'answer'  : answer
  }

  # return to main page and send response back
  return render_to_response(
    'interface/index.html', 
    {
      'status'        : 'OK',
      'notice_message': notice_message, 
      'conversation'  : conversation,
    }, 
    context_instance=RequestContext(request)
  )

def debug_session_file(data):
  for pred,value in data.items():
    print str(pred) + ": " + str(value)

