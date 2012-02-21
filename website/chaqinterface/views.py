from django.shortcuts import render_to_response
from django.template import RequestContext
from chaqinterface.models import Conversation
from django.contrib.auth.models import User

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

  # get answer from Inference Engine and Knowledge Base or PyAIML interpreter
  k = aiml.Kernel()
  k.learn("PyAIML/std-startup.xml")

  # k.bootstrap(brainFile = "PyAIML/standard.brn")

  k.respond('load aiml b')
  answer = k.respond(request.POST['question'])
  # insert question/answer into user's logs
  # conversation = new Conversation
  # conversation.question = request.POST['question']
  # conversation.answer   = response
  conversation = {
    'question': request.POST['question'],
    'answer'  : answer,
  }

  # return to main page and send response back
  return render_to_response(
    'interface/index.html', 
    {
      'status'        : 'OK',
      'notice_message':'Question asked...', 
      'conversation'  : conversation,
    }, 
    context_instance=RequestContext(request)
  )