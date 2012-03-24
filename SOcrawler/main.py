#!/usr/bin/python
"""
It would be great to try and create some sort of graph of all the questions/answers and see if they point to one another, also trying to get the best one out of the connected ones. For example, say there are 5 questions regarding parsing HTML with PHP: x1, x2, x3, x4, x5. From these 5, x3 and x4 have a reference of x1 as being the same question with a very good answer. Can we find out about this kind of stuff? I think we should, if we filter through <a> tags that have a link following the patter of the questions: stackoverflow.com/questions/QuestionID/some-page-title - where we are looking for QuestionID. But how do we then know that x1, x2 and x5 are also connected??? Could search engine 'tech/methods' help us in this??? Or semantic analysis on the bodies of texts? This would be very important especially in multiple versions of the same question. For example how you would do the same think in PHP4 vs PHP5, or Python 2 vs Python 3. The inference engine should realize there is a newer version of an answer, but from a different question, and use that as the basis of the answer generation.

A new mysql user/db are used for this as it is a separate component of the system and also better for security purposes. In the case an attacker will penetrate the database, it will only have access to public information you can easily access anyway ...

It would also be great to have the below code incorporated into a class StackOverflowCrawler which is implementing a Crawler Interface. Then use a main script, running every x minutes on a Cron job, implementing the Factory Design pattern and randomly calling all the available crawlers - something like this could be used for when multiple sites are crawled for information, but we need a standard way of fetching information from each of those sites: question and accepted/correct/viable answer ... especially from sites that do not have an available API and the 'standard' route of following URIs has to be followed, such as a Search Engine would have to.

Should I also save information about a user such as reputation and accept rate?
"""

import sys, json, urllib2, gzip, StringIO, random, time, marshal, os.path, MySQLdb
# httplib.HTTPConnection.debuglevel = 1

def log(string):
    string = str(string) + "\n"
    # print string
    with open("/home/pavel/www/Chaq/SOcrawler/log.txt", "a") as logfile:
        logfile.write(string)

# The start date to start crawling from: 2008-01-01 00:00:00
start_date_timestamp = 1217548800
# Set crawler's user-agent - in case of any problems SO will know who/where to contact me
_user_agent = 'ChaqCrawler/1.0 +http://www.mpavel.ro/socrawler/'
# Save crawled questions data for the current session
_data = None
# List of unreachable answers when trying to fetch them after loading the question
_unreachable_answers = []
# List of answer IDs, all to be fetched at once
_answers_list = []
# The number of how answers to process at once
# IMPORTANT! Must be a divisor of 100, so that
_answers_batch = 100
# Database connection
try:
    _db = MySQLdb.connect(host = 'localhost',
                          user = 'crawler',
                          passwd = 'crawlpass12',
                          db = 'socrawler')
except MySQLdb.Error, e:
    log("Error %d: %s" % (e.args[0], e.args[1]))
    sys.exit(1)

def getResource(uri):
    request = urllib2.Request(uri)
    # Setting User-Agent for crawler
    request.add_header('User-Agent', _user_agent)
    # Tell server we can accept gzip encoding
    request.add_header('Accept-encoding', 'gzip')

    opener  = urllib2.build_opener()

    try:
        first_data_stream = opener.open(request);
    except urllib2.URLError:
        log('Error opening URL: ' + uri)
        return False

    # Dictionary of headers sent in response after connecting to server
    log(first_data_stream.headers)

    compressed_data = first_data_stream.read()
    # Get the compressed data from the memory and into a file-like object
    compressed_stream = StringIO.StringIO(compressed_data)
    # GzipFile containing the compressed data from the server
    gzipper = gzip.GzipFile(fileobj = compressed_stream)
    # The uncompressed data
    data = gzipper.read()

    return data

def saveUnreachableAnswers():
    global _unreachable_answers

    for answer in _answers_list:
        _unreachable_answers.append(answer)
    # Save to file for use next time crawler loads
    saveFile(_unreachable_answers, 'unreachableAnswers.ses')
    log('Unreachable answers this session: ' + str(_unreachable_answers))

def getAnswers():
    global _answers_list
    global _answers_batch

    answer_count = len(_answers_list)
    i = 0

    while (answer_count != 0):
        # Get a subset of _answers_batch items from the available answers
        short_answers_list = _answers_list[0:_answers_batch]
        # Now remove those elements from the global list
        _answers_list = _answers_list[_answers_batch:]
        # Recount _answers_list for next iteration of while loop
        answer_count = len(_answers_list)

        answers = '';
        for answerID in short_answers_list:
            answers += str(answerID) + ';'
        # remove the last ';' so we don't break the URI
        answers = answers[:-1]
        
        answers_url = 'http://api.stackoverflow.com/1.1/answers/' + str(answers) + '?body=true&comments=false&pagesize=' + str(_answers_batch)

        log(answers_url)

        answers = getResource(answers_url)
        answers = json.loads(answers)

        if answers != False:
            answers = answers['answers']    
            # Add the answer to the db
            for answer in answers:
                saveAnswer(answer)
        
        i += 1
    # If there are answers unreachable due to the service being unavailable or whatever else
    # we add them to a queue and save the file for the next time the crawler runs
    saveUnreachableAnswers()

def saveAnswer(answer):
    global _db
    answerID   = int(answer['answer_id'])
    questionID = int(answer['question_id'])
    date       = str(answer['creation_date'])
    up_vote    = int(answer['up_vote_count'])
    down_vote  = int(answer['down_vote_count'])
    score      = int(answer['score'])
    body       = unicode(answer['body'])
    body       = body.encode('utf-8')

    query_values = (answerID, questionID, date, up_vote, down_vote, score, body)
    c = _db.cursor()
    try:
        c.execute("""
        INSERT INTO 
            answer(id, qid, date, up_vote, down_vote, score, body) 
            VALUES(%s, %s, %s, %s, %s, %s, %s)""", query_values)
    except MySQLdb.Error, e:
        log("Error %d: %s" % (e.args[0], e.args[1]))


def getQuestions(startDate, endDate, tag):
    global _data

    question_url = 'http://api.stackoverflow.com/1.1/questions?answers=false&body=true&comments=false&sort=hot&pagesize=100&tagged=' + str(tag) + '&fromdate=' + str(startDate) + '&todate=' + str(endDate)

    log(question_url)

    data = getResource(question_url)
    _data = json.loads(data)

    return True

def saveQuestion(question, tag):
    global _unreachable_answers
    global _answers_list
    global _answers_batch
    global _db

    if 'accepted_answer_id' in question:
        answerID = question['accepted_answer_id']
    else:
        # Just return if there is no accepted answer to the question ...
        # Or I could send the question to a special function to fetch the answer with top votes, and add that to the _answers_list
        return
    questionID     = int(question['question_id'])
    title          = unicode(question['title'])
    title          = title.encode('utf-8')
    body           = unicode(question['body'])
    body           = body.encode('utf-8')
    tags           = str(question['tags']) # the tags from SO
    date           = str(question['creation_date'])
    up_vote        = int(question['up_vote_count'])
    down_vote      = int(question['down_vote_count'])
    score          = int(question['score'])
    favorite_count = int(question['favorite_count'])
    viewed         = int(question['view_count'])

    # insert question details into database
    query_values = (questionID, title, body, tags, date, up_vote, down_vote, score, favorite_count, viewed)
    c = _db.cursor()
    try:
        c.execute("""
        INSERT INTO 
            question(id, title, body, tags, date, up_vote, down_vote, score, favorite_count, viewed) 
            VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", query_values)
        # add answerID to list
        _answers_list.append(answerID)
    except MySQLdb.Error, e:
        log("Error %d: %s" % (e.args[0], e.args[1]))

def loadFile(filename):
    if os.path.isfile(filename):
        tags = {}
        sessionFile = file(filename, "rb")
        tags = marshal.load(sessionFile)
        sessionFile.close()
        return tags
    return False

def saveFile(data, filename):
    sessionFile = file(filename, "wb")
    marshal.dump(data, sessionFile)
    sessionFile.close();

if __name__ == "__main__":
    # log("\n=================== STACK OVERFLOW CRAWLER START ===================")
    log("\n=================== " + time.strftime("%Y-%m-%d %H:%M:%S") + " ============================")
    log("====================================================================\n")

    # First thing to do is check if there are any answers that haven't been able to be loaded on last crawl, and fetch them
    unreachable_answers = loadFile('unreachableAnswers.ses')
    if unreachable_answers is not False:
        for answer in unreachable_answers:
            _answers_list.append(answer)
        if len(_answers_list) > 0:
            getAnswers()
            log('Retrying previously unreachable answers: ' + str(unreachable_answers))

    # After this, continue with any new questions, incrementing the dates, etc
    session_filename = 'session.ses'
    # Load crawler session file, containing the tags and last start date for each tag
    tags = {}
    tags = loadFile(session_filename)
    # log(tags)
    if not tags:
        # Create new session.ses file, assuming everything starts from 0 again
        # Meaning, the crawler is reset, and start_date_timestamp is back to 2007-01-01
        # Rather than what it used to be for each tag.
        tag_list = ['c#', 'java', 'php', 'javascript', 'jquery', 'android', 'iphone', 'c++', 'asp.net', '.net', 'python', 'mysql', 'html', 'sql', 'ruby-on-rails', 'css', 'ajax', 'linux', 'django', 'json', 'perl', 'git', 'wordpress']
        tags = {}
        for tag in tag_list:
            tags[tag] = start_date_timestamp
        # Now that we have all the tags reset to the start date, write them to file
        saveFile(tags, session_filename)

    # Select a random tag from the list to crawl more questions
    random_tag_key = random.randrange(1,len(tags),1) - 1
    # Get the tag, as selected from the random number
    tag = tags.keys()[random_tag_key]
    start_date = tags[tag]

    # Calculate end date, add 345600 to start date (+4 days)
    end_date = start_date + 345600

    now = int(time.time())
    # Check if end_date_timestamp is less than now
    if end_date > now:
        end_date = now
    
    log('Random tag: ' + tag + ' | Start: ' + time.ctime(start_date) + ' | End: ' + time.ctime(end_date))

    # Start the actual crawl process, by fetching the questions
    # Plus, if the crawl is successfull, write the new tags dictionary, containing the updated end_date, to the session file.
    if getQuestions(start_date, end_date, tag):
        # Before saving, update the tags dictionary to contain the last end_date
        tags[tag] = end_date
        saveFile(tags, session_filename)
    
    total_questions = _data['total']
    if total_questions > 0:
        for question in _data['questions']:
            saveQuestion(question, tag)
        # Now that we have all questions, fetch the answers for all of them, based on the answer IDs
        getAnswers()

    else:
        log('No questions between ' + time.ctime(start_date) + ' and ' + time.ctime(end_date))