from flask import Flask, render_template, flash, redirect, request, url_for, jsonify
from flask_wtf import Form
from wtforms.fields import StringField, SubmitField, DateField, SelectField
from wtforms.validators import DataRequired, ValidationError, Email
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_, or_
import datetime


app = Flask(__name__)

app.secret_key = 'development key'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lab2.db'
db = SQLAlchemy(app)


# Database table
class BookingDetails(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False, unique=True)
    email = db.Column(db.String(64), nullable=False)
    node = db.Column(db.Integer, nullable=False)
    GPU = db.Column(db.Integer, nullable=False)
    startDate = db.Column(db.Date, nullable=False)
    startTime = db.Column(db.Integer, nullable=False)
    endTime = db.Column(db.Integer, nullable=False)  # should be calculated with startTime and duration
    endDate = db.Column(db.Date, nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    start = db.Column(db.String, nullable=False)
    end = db.Column(db.String, nullable=False)

    def __repr__(self):
        return 'GPU {} of Node {} is currently used by {} for {} hours'.format(self.GPU, self.node, self.email, self.duration)


# Form
class BookingForm(Form):
    email = StringField(validators=[DataRequired(), Email("This field requires a valid email address")])
    node = SelectField(coerce=int, choices=[(60, 60), (61, 61), (63, 63)], render_kw={"class": "form-control"})
    GPU = SelectField(coerce=int, choices=[(i, i) for i in range(1, 5)], render_kw={"class": "form-control"})
    startDate = DateField(format='%Y-%m-%d', validators=[DataRequired('please select start date')])
    startTime = SelectField("Start time", coerce=int, choices=[(i, i) for i in range(0, 24)], render_kw={"class": "form-control"})
    duration = SelectField(coerce=int, choices=[(i, i) for i in range(1, 25)], render_kw={"class": "form-control"})
    submit = SubmitField('Book')


class GPUAvailabilityForm(Form):
    node = SelectField('Choose the Node to check', coerce=int, choices=[(60, 60), (61, 61), (63, 63)], render_kw={"class": "form-control"})
    submit = SubmitField('Check')


# Routes
# Navigation bar
@app.route('/')
@app.route('/base')
def index():
    return render_template('base.html')


@app.route('/book', methods=['GET', 'POST'])
def book():
    # require user's input and return the user's input as a class form
    form = BookingForm()

    # validate the submission within the form
    if form.validate_on_submit():
        if form.startDate.data < datetime.datetime.now().date():
            flash('You cannot make booking in the past')
            return redirect(url_for('book'))
        else:
            # constant
            form_start_time = form.startTime.data
            form_end_time = form_start_time + form.duration.data
            form_start_date = form.startDate.data
            form_node = form.node.data
            form_gpu = form.GPU.data
            if form_end_time >= 24:
                form_end_date = form_start_date + datetime.timedelta(days=1)
            else:
                form_end_date = form_start_date
    else:
        return render_template('book.html', title='Book GPU', form=form)

    # booking collisions filtered by start date, end date, node and GPU
    booking_collisions = db.session.query(BookingDetails).filter(or_(BookingDetails.startDate == form_start_date
                                                                     , BookingDetails.endDate == form_start_date
                                                                     , BookingDetails.endDate == form_end_date))\
        .filter(and_(BookingDetails.node == form_node, BookingDetails.GPU == form_gpu))

    for booking_collision in booking_collisions:
        # convert booking collision time into same time scale as the user input
        if booking_collision.startDate < form_start_date:
            booking_collision_start_time = booking_collision.startTime - 24
        elif booking_collision.startDate > form_start_date:
            booking_collision_start_time = booking_collision.startTime + 24
        else:
            booking_collision_start_time = booking_collision.startTime
        if booking_collision.endDate > form_start_date:
            booking_collision_end_time = booking_collision.endTime + 24
        else:
            booking_collision_end_time = booking_collision.endTime
        if form_start_time < booking_collision_end_time and form_end_time > booking_collision_start_time:
            flash('From the date {} and time {}, to the date {} and time {} is already booked by {}'.format(
                 booking_collision.startDate, booking_collision.startTime, booking_collision.endDate,
                 booking_collision.endTime, booking_collision.email))
            return redirect(url_for('book'))
    if form_end_time >= 24:
        end_time = form.duration.data - (24 - form_start_time)
        end_date = form_start_date + datetime.timedelta(days=1)
    else:
        end_time = form.duration.data + form_start_time
        end_date = form_start_date

    # make booking
    if form_start_time < 10 and end_time < 10:
        start = str(form_start_date) + "T" + "0" + str(form_start_time) + ":00:00"
        end = str(end_date) + "T" + "0" + str(end_time) + ":00:00"
    elif form_start_time < 10 < end_time:
        start = str(form_start_date) + "T" + "0" + str(form_start_time) + ":00:00"
        end = str(end_date) + "T" + str(end_time) + ":00:00"
    elif form_start_time > 10 > end_time:
        start = str(form_start_date) + "T" + str(form_start_time) + ":00:00"
        end = str(end_date) + "T" + "0" + str(end_time) + ":00:00"
    else:
        start = str(form_start_date) + "T" + str(form_start_time) + ":00:00"
        end = str(end_date) + "T" + str(end_time) + ":00:00"
    booking = BookingDetails(email=form.email.data, node=form_node, GPU=form_gpu, startDate=form_start_date,
                             startTime=form_start_time, endTime=end_time, endDate=end_date, duration=form.duration.data,
                             start=start, end=end)
    db.session.add(booking)
    db.session.commit()
    flash('Booking success!')
    return redirect(url_for('book'))


@app.route('/cancel_booking', methods=['GET', 'POST'])
def cancel_booking():
    if request.method == 'POST':
        # get if checkbox is ticked
        values = request.form.getlist("cancel_choice")
        # if any of the checkbox is ticked
        if values is not []:
            for value in values:
                # delete the ticked bookings from the database
                BookingDetails.query.filter_by(id=int(value)).delete()
                db.session.commit()
            flash('Booking Cancelled')
            return redirect(url_for('cancel_booking'))
        # if no checkbox is ticked
        else:
            # Ask user for their email
            email = str(request.form['email'])
            if email == "":
                flash("Please enter your email")
                return redirect(url_for('cancel_booking'))
            # Filter all the bookings with the user's email
            bookings = BookingDetails.query.filter_by(email=email).all()
            choices = [(booking.id, 'GPU {} of Node {} started at {} from {}, to {} at {}'.format(booking.GPU,
                                                                                                  booking.node,
                                                                                                  booking.startDate,
                                                                                                  booking.startTime,
                                                                                                  booking.endDate,
                                                                                                  booking.endTime)) for booking in bookings]
            # If no bookings are made under this email
            if not choices:
                flash("You have no bookings available to cancel")
                return redirect(url_for('cancel_booking'))
            return render_template("cancel_booking.html", email=email, choices=choices)
    # If email is not entered
    else:
        if "email" not in request.form:
            return render_template("cancel_booking.html")

    return render_template("cancel_booking.html")


@app.route('/gpu_availability', methods=['GET', 'POST'])
def gpu_availability():
    form = GPUAvailabilityForm()
    if request.method == 'POST':
        if form.node.data == 60:
            # return calendar for node60
            return render_template('json1.html')
        elif form.node.data == 61:
            return render_template('json2.html')
        elif form.node.data == 63:
            return render_template('json3.html')
    else:
        return render_template('gpu_availability.html', title='GPU Availability', form=form)


@app.route('/data1')
def return_data_for_node_one():
    json_bookings = []
    bookings = BookingDetails.query.filter_by(node=60)
    for booking in bookings:
        event = dict()
        if booking.GPU == 1:
            event['title'] = 'GPU {} is currently used by {} for {} hours'.format(booking.GPU, booking.email, booking.duration)
            event['start'] = booking.start
            event['end'] = booking.end
            event['color'] = 'rgb(252, 128, 128)'
        elif booking.GPU == 2:
            event['title'] = 'GPU {} is currently used by {} for {} hours'.format(booking.GPU, booking.email, booking.duration)
            event['start'] = booking.start
            event['end'] = booking.end
            event['color'] = 'rgb(252, 194, 3)'
        elif booking.GPU == 3:
            event['title'] = 'GPU {} is currently used by {} for {} hours'.format(booking.GPU, booking.email, booking.duration)
            event['start'] = booking.start
            event['end'] = booking.end
            event['color'] = 'rgb(3, 161, 252)'
        else:
            event['title'] = 'GPU {} is currently used by {} for {} hours'.format(booking.GPU, booking.email, booking.duration)
            event['start'] = booking.start
            event['end'] = booking.end
            event['color'] = 'rgb(3, 252, 128)'
        json_bookings.append(event)
    return jsonify(json_bookings)


# Jquery data value passed to json.html
@app.route('/data2')
def return_data_for_node_two():
    json_bookings = []
    bookings = BookingDetails.query.filter_by(node=61)
    for booking in bookings:
        event = dict()
        if booking.GPU == 1:
            event['title'] = 'GPU {} is currently used by {} for {} hours'.format(booking.GPU, booking.email, booking.duration)
            event['start'] = booking.start
            event['end'] = booking.end
            event['color'] = 'rgb(252, 128, 128)'
        elif booking.GPU == 2:
            event['title'] = 'GPU {} is currently used by {} for {} hours'.format(booking.GPU, booking.email, booking.duration)
            event['start'] = booking.start
            event['end'] = booking.end
            event['color'] = 'rgb(252, 194, 3)'
        elif booking.GPU == 3:
            event['title'] = 'GPU {} is currently used by {} for {} hours'.format(booking.GPU, booking.email, booking.duration)
            event['start'] = booking.start
            event['end'] = booking.end
            event['color'] = 'rgb(3, 161, 252)'
        else:
            event['title'] = 'GPU {} is currently used by {} for {} hours'.format(booking.GPU, booking.email, booking.duration)
            event['start'] = booking.start
            event['end'] = booking.end
            event['color'] = 'rgb(3, 252, 128)'
        json_bookings.append(event)
    return jsonify(json_bookings)


@app.route('/data3')
def return_data_for_node_three():
    json_bookings = []
    bookings = BookingDetails.query.filter_by(node=63)
    for booking in bookings:
        event = dict()
        if booking.GPU == 1:
            event['title'] = 'GPU {} is currently used by {} for {} hours'.format(booking.GPU, booking.email, booking.duration)
            event['start'] = booking.start
            event['end'] = booking.end
            event['color'] = 'rgb(252, 128, 128)'
        elif booking.GPU == 2:
            event['title'] = 'GPU {} is currently used by {} for {} hours'.format(booking.GPU, booking.email, booking.duration)
            event['start'] = booking.start
            event['end'] = booking.end
            event['color'] = 'rgb(252, 194, 3)'
        elif booking.GPU == 3:
            event['title'] = 'GPU {} is currently used by {} for {} hours'.format(booking.GPU, booking.email, booking.duration)
            event['start'] = booking.start
            event['end'] = booking.end
            event['color'] = 'rgb(3, 161, 252)'
        else:
            event['title'] = 'GPU {} is currently used by {} for {} hours'.format(booking.GPU, booking.email, booking.duration)
            event['start'] = booking.start
            event['end'] = booking.end
            event['color'] = 'rgb(3, 252, 128)'
        json_bookings.append(event)
    return jsonify(json_bookings)


if __name__ == '__main__':
    app.debug = True
    app.run(host='127.0.0.1', port=5000)
