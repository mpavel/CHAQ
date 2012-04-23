#!/usr/bin/python
"""
Small script that fetches all text from the database (Q&A) and saves it
as files so it can be used with NLTK.
"""

import sys, MySQLdb
from BeautifulSoup import BeautifulSoup

def strip(html):
    s = ""

    if html is not None:
        tags_to_keep = ['code', 'pre']
        soup = BeautifulSoup(html)
        allSoup = soup.findAll(True)
        if len(allSoup) == 0:
            s += unicode(''.join(soup.findAll(text=True)))
        else:
            for tag in allSoup:
                # Remove all tags but [tags_to_keep]
                if tag.name in tags_to_keep:
                    s += unicode(tag)
                else:
                    s += unicode(''.join(tag.findAll(text=True)))
    return s
    # return ''.join(BeautifulSoup(html).findAll(text=is_not_code))

def saveFile(data, filename):
    f = open(filename, "a+")
    f.write(data)
    f.close()

def log(string):
    string = str(string) + "\n"
    print string

# dictionary containing all Q&A
_questions = [] # Format: {'question': [id, title, body, tags], 'answer': [id, body] }
# list of tags used to crawl Stack Overflow, from SOcrawler
tag_list = set(['c#', 'java', 'php', 'javascript', 'jquery', 'android', 'iphone', 'c++', 'asp.net', '.net', 'python', 'mysql', 'html', 'sql', 'ruby-on-rails', 'css', 'ajax', 'linux', 'django', 'json', 'perl', 'git', 'wordpress', 'c'])

# Database connection
try:
    _db = MySQLdb.connect(host = 'localhost',
                          user = 'crawler',
                          passwd = 'crawlpass12',
                          db = 'socrawler')
except MySQLdb.Error, e:
    log("Error %d: %s" % (e.args[0], e.args[1]))
    sys.exit(1)

# def getAnswer(questionID):
#     global _db
#     c = _db.cursor()
#     try:
#         c.execute("""
#         SELECT *
#         FROM answer
#         WHERE qid = %s""", questionID)
#     except MySQLdb.Error, e:
#         log("Error %d: %s" % (e.args[0], e.args[1]))
    
#     return c.fetchone()


def getQuestions():
    global _questions
    global _db
    c = _db.cursor()

    try:
        c.execute("""
        SELECT 
            question.id AS questionID,
            question.title AS question,
            question.body AS questionBody,
            question.tags AS tags,
            answer.id AS answerID,
            answer.body AS answer
        FROM question
        LEFT JOIN answer 
        ON question.id = answer.qid 
        ORDER BY question.id ASC
        # LIMIT 0,100000
        """)
    except MySQLdb.Error, e:
        log("Error %d: %s" % (e.args[0], e.args[1]))
    
    while (1):
        row = c.fetchone()
        if row == None:
            break

        item = {
            'questionID': row[0], 
            'question': strip(row[1]), 
            'questionBody': strip(row[2]), 
            'tags': row[3],
            'answerID': row[4], 
            'answer': strip(row[5])
        }
        _questions.append(item)

    # print "Number of rows returned: %d" % c.rowcount

if __name__ == "__main__":

    getQuestions()

    print 'Items are now in memory.'

    for item in _questions:
        print item['questionID']
        tags = set(eval(item['tags'].encode('utf-8')))

        # intersect the row's tags with the tags from crawler, to only get the common used ones
        tags_to_use = tag_list & tags
        if len(tags_to_use) == 0:
            print 'Exception: ' + str(tags)
            tags_to_use = ['unknown']

        # Get the data for each Q&A
        data = item['question'].encode('utf-8') + '\n'
        data += item['questionBody'].encode('utf-8') + '\n'
        data += item['answer'].encode('utf-8') + '\n'
        data += '\n'
        
        for tag in tags_to_use:
            # check if the first char in tag is '.' and prepend '_' if so
            # that's because '.<name>' files are hidden by default ...
            if tag[0] == '.':
                tag = '_' + tag.encode('utf-8')
            filename = sys.path[0] + '/text/' + tag.encode('utf-8') + '.txt'
            # And append that data in multiple files according to the tags associated
            saveFile(data, filename)