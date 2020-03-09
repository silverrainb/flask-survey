from flask import Flask, request, render_template, redirect, flash, make_response, \
    session
from flask_debugtoolbar import DebugToolbarExtension
from surveys import surveys

RESPONSES_KEY = "storage"
CURRENT_SURVEY_KEY = 'current_survey'

app = Flask(__name__)
app.config['SECRET_KEY'] = "flasksurveys"
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
debug = DebugToolbarExtension(app)


@app.route('/')
def start_survey():
    return render_template('choose_survey.html', surveys=surveys)


@app.route('/', methods=['POST'])
def choose_survey():
    survey_id = request.form['survey_code']

    if request.cookies.get(f'completed_{survey_id}'):
        return render_template('already-done.html')

    survey = surveys[survey_id]
    session[CURRENT_SURVEY_KEY] = survey_id

    return render_template('start_survey.html', survey=survey)


@app.route('/begin', methods=["POST"])
def begin_questions():
    """Clear the session of responses."""
    session[RESPONSES_KEY] = []
    return redirect("/questions/0")


@app.route('/questions/<int:question_id>')
def show_question(question_id):
    """Display current question."""
    responses = session.get(RESPONSES_KEY)
    survey_code = session[CURRENT_SURVEY_KEY]
    survey = surveys[survey_code]

    if responses is None:
        # trying to access question page too soon
        return redirect("/")
    if len(responses) == len(survey.questions):
        # answered all question
        return redirect("/complete")
    if len(responses) != question_id:
        # trying to access questions out of order
        flash(f"Invalid question id: {question_id}")
        return redirect(f"/questions/{len(responses)}")

    question = survey.questions[question_id]
    return render_template("question.html", question_num=question_id,
                           question=question)


@app.route('/answer', methods=["POST"])
def answer():
    """Save response and redirect to next question."""
    # get the response/answer choice
    choice = request.form['answer']
    text = request.form.get("text", "")
    # add the choice to the session
    responses = session[RESPONSES_KEY]
    # this change is not picked up because a mutable object (list) is changed.
    responses.append({"choice": choice, "text": text})
    # so either mark it as modified yourself
    session.modified = True
    # or reassign session[RESPONSES_KEY] to a new value, which is the modified list.
    # https://flask.palletsprojects.com/en/1.1.x/api/#flask.session
    # session[RESPONSES_KEY] = responses

    # add this response to the session
    session[RESPONSES_KEY] = responses
    survey_code = session[CURRENT_SURVEY_KEY]
    survey = surveys[survey_code]

    if len(responses) == len(survey.questions):
        return redirect('finish')
    else:
        return redirect(f'/questions/{len(responses)}')


@app.route('/finish')
def complete():
    survey_id = session[CURRENT_SURVEY_KEY]
    survey = surveys[survey_id]
    responses = session[RESPONSES_KEY]

    html = render_template("finish.html",
                           survey=survey,
                           responses=responses)

    # Set cookie noting this survey is done so they can't re-do it
    response = make_response(html)
    response.set_cookie(f"completed_{survey_id}", "yes", max_age=60)
    return response
