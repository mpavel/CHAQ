import sys, json, httplib, urllib2, gzip, StringIO, random, time
import marshal, os.path
httplib.HTTPConnection.debuglevel = 1

# The start date to start crawling from: 2007-01-01 00:00:00
start_date_timestamp = 1199145600
# Set crawler's user-agent - in case of any problems SO will know who/where to contact me
_user_agent = 'ChaqCrawler/1.0 +http://www.mpavel.ro/socrawler/'
# Save crawled questions for the session
_questions = None

def getAnswer(answerID):
    return

def saveAnswer(answer, questionID):
    return

def getQuestions(startDate, endDate, tag):

    global _questions

    question_url = 'http://api.stackoverflow.com/1.1/questions?answers=false&body=true&comments=false&sort=hot&pagesize=100&tagged=' + str(tag) + '&fromdate=' + str(startDate) + '&todate=' + str(endDate)

    print question_url

    request = urllib2.Request(question_url)
    # Setting User-Agent for crawler
    request.add_header('User-Agent', _user_agent)
    # Tell server we can accept gzip encoding
    request.add_header('Accept-encoding', 'gzip')

    opener  = urllib2.build_opener()

    try:
        first_data_stream = opener.open(request);
    except urllib2.URLError:
        print 'Error opening URL: ' + question_url
        return False

    # Dictionary of headers sent in response after connecting to server
    print first_data_stream.headers

    compressed_data = first_data_stream.read()
    # Get the compressed data from the memory and into a file-like object
    compressed_stream = StringIO.StringIO(compressed_data)
    # GzipFile containing the compressed data from the server
    gzipper = gzip.GzipFile(fileobj = compressed_stream)
    # The uncompressed JSON data
    data = gzipper.read()

    print data

    _questions = json.loads(data)

    return True

def saveQuestion(question, tag):
    return

def loadTags(filename = 'session.ses'):
    if os.path.isfile(filename):
        tags = {}
        sessionFile = file(filename, "rb")
        tags = marshal.load(sessionFile)
        sessionFile.close()
        return tags
    return False

def saveTags(data, filename = 'session.ses'):
    sessionFile = file(filename, "wb")
    marshal.dump(data, sessionFile)
    sessionFile.close();

if __name__ == "__main__":
    print '=================== STACK OVERFLOW CRAWLER START ==================='
    print '=================== ' + time.strftime("%Y-%m-%d %H:%M:%S") + ' ============================'
    print '===================================================================='

    # First thing to do is check if there are any answers that haven't been able to be loaded on last crawl, and fetch them

    # After this, continue with any new questions, incremending the dates, etc
    session_filename = 'session.ses'
    # Load crawler session file, containing the tags and last start date for each tag
    tags = {}
    tags = loadTags(session_filename)
    if not tags:
        # Create new session.ses file, assuming everything starts from 0 again
        # Meaning, the crawler is reset, and start_date_timestamp is back to 2007-01-01
        # Rather than what it used to be for each tag.
        tag_list = ['c#', 'java', 'php', 'javascript', 'jquery', 'android', 'iphone', 'c++', 'asp.net', '.net', 'python', 'mysql', 'html', 'sql', 'ruby-on-rails', 'css', 'ajax', 'linux', 'django', 'json', 'perl', 'git', 'wordpress']
        tags = {}
        for tag in tag_list:
            tags[tag] = start_date_timestamp
        # Now that we have all the tags reset to the start date, write them to file
        saveTags(tags, session_filename)

    # Select a random tag from the list to crawl more questions
    random_tag_key = random.randrange(1,len(tags),1) - 1
    # Get the tag, as selected from the random number
    # tag = tags.keys()[random_tag_key]
    tag = 'php'
    start_date = tags[tag]

    # Calculate end date, add 345600 to start date (+4 days)
    end_date = start_date + 1045600

    now = int(time.time())
    # Check if end_date_timestamp is less than now
    if end_date > now:
        end_date = now
    
    print 'random tag: ' + tag + ' | start: ' + str(start_date) + ' | end: ' + str(end_date)

    # Start the actual crawl process, by fetching the questions
    # Plus, if the crawl is successfull, write the new tags dictionary, containing the updated end_date, to the session file.
    if getQuestions(start_date, end_date, tag):
        # Before saving, update the tags dictionary to contain the last end_date
        tags[tag] = end_date
        saveTags(tags, session_filename)
    
    total_questions = _questions['total']
    if total_questions > 0:
        for question in _questions['questions']:
            questionID = question['question_id']
            body = question['body']
            tags = question['tags']
            answerID = question['accepted_answer_id']
    else:
        print 'No questions between ' + time.ctime(start_date) + ' and ' + time.ctime(end_date)