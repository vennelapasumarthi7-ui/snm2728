from flask import Flask,request,redirect,url_for,render_template,flash,session,jsonify,send_file
from io import BytesIO #used to handle file data in memory
from flask_session import Session #used to manage session data in flask
from otp import genotp #used to generate otps 
from cmail import send_mail # used to send email
from stoken import endata,dndata  # used to sign data passing through urls
from mysql.connector import (connection) #used to connect mysql server
import flask_excel as excel #used to generate data in excel format
import re
mydb=connection.MySQLConnection(user='root',host='localhost',password='admin',database='snmdb')
app=Flask(__name__)
excel.init_excel(app) #initialize excel in flask app
app.secret_key='code24'
app.config['SESSION_TYPE']='filesystem' #configure session type to store data in file system
Session(app) # initialize session layer
@app.route('/')
def index():
    return render_template('welcome.html')
@app.route('/register',methods=['GET','POST'])
def register():
    if request.method=="POST":
        username=request.form['username']
        useremail=request.form['useremail']
        userpassword=request.form['userpassword']
        userphone_no=request.form['userphone_no']
        try:
            cursor=mydb.cursor()
            cursor.execute('select count(useremail) from userdata where useremail=%s',[useremail])
            count_email=cursor.fetchone() #(1,)
            cursor.close()
        except Exception as e:
            print(e)
            flash('could not verify email')
            return redirect(url_for('register'))
        else:
            if count_email[0]==0:
                generated_otp=genotp()#G8bD6m
                userdata={'username':username,'useremail':useremail,'userpassword':userpassword,
                        'user_phone':userphone_no,'generated_otp':generated_otp}
                subject=f'User OTP Verification'
                body=f'hii {username} Use the given OTP: {generated_otp}'
                send_mail(to=useremail,subject=subject,body=body)
                flash('OTP has been sent to given mail' )
                return redirect(url_for('otpverify',server_data=endata(userdata)))
            elif count_email[0]==1:
                flash('email already existed')
                return redirect(url_for('register'))
    return render_template('register.html')
@app.route('/otpverify/<server_data>',methods=['GET','POST'])
def otpverify(server_data):
    if request.method=='POST':
        try:
            d_data=dndata(server_data)
        except Exception as e:
            print(e)
            flash('couldnot verify  otp')
            return redirect(url_for('register'))
        userotp=request.form['otp']
        if d_data['generated_otp']==userotp:
            try:
            #db connection
                cursor=mydb.cursor()
                cursor.execute('insert into userdata(username,useremail,userpassword,userphone) values(%s,%s,%s,%s)',[d_data['username'],d_data['useremail'],d_data['userpassword'],d_data['user_phone']])
                mydb.commit() #used to save data permanently
                cursor.close()
            except Exception as e:
                print(e)
                flash('DB connection fail could not save data ')
                return redirect(url_for('register'))
            else:
                flash('Details registered succesfully')
                return redirect(url_for('login'))
        else:
            flash('OTP was wrong')
            return redirect(url_for('otpverify',server_data=server_data))

    return render_template('otpVerify.html')
@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        login_email=request.form['useremail']
        login_password=request.form['userpassword']
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select count(useremail) from userdata where useremail=%s',[login_email])
            email_count=cursor.fetchone() #(1,)
            if email_count[0] == 1:
                 cursor.execute('select userpassword from userdata where useremail=%s',[login_email])
                 stored_password=cursor.fetchone()
                 cursor.close()
                 if stored_password[0]==login_password:
                     print(session)
                     session['user']=login_email #store email in session to identify user in other pages
                     print(session)
                     return redirect(url_for('dashboard'))
               
                 else:
                    flash('wrong password')
                    return redirect(url_for('login'))
            elif email_count[0] ==0:
                flash('email not found')
                return redirect(url_for('login'))
        except Exception as e:
            print(e)
            flash('couldnot verify login details')
            return redirect(url_for('login'))
    return render_template('login.html')
@app.route('/dashboard')
def dashboard():

    return render_template('dashboard.html')
@app.route('/logout')
def logout():
    if not session.get('user'):
        flash('to access dashboard login is first')
        return redirect(url_for('login'))
    try:
        session.pop('user') #remove user email from session to logout
        flash('loggedout successfully')
        return redirect(url_for('login'))
    except Exception as e:
        print(e)
        flash('couldnot logout')
        return redirect(url_for('dashboard'))
@app.route('/forgot',methods=['GET','POST'])
def forgot():
    if request.method=='POST':
        forgot_email=request.form['useremail']
        try:
                cursor=mydb.cursor()
                cursor.execute('select count(useremail) from userdata where useremail=%s',[forgot_email])
                count_email=cursor.fetchone() #(1,)
                cursor.close()
        except Exception as e:
            print(e)
            flash('could not verify email')
            return redirect(url_for('forgot'))
        else:
            if count_email[0]==1:
                subject=f"Re-set link for forgot password SNM App"
                body=f"use the link to update password: {url_for('newpassword',data=endata(forgot_email),_external=True)}"
                send_mail(to=forgot_email,subject=subject,body=body)
                flash('Re-set link has been sent to given  mail')
                return redirect(url_for('forgot'))
            elif count_email[0]==0:
                flash('Email not found')
                return redirect(url_for('forgot'))

    return render_template('forgot.html')
@app.route('/newpassword/<data>', methods=['GET', 'PUT'])
def newpassword(data):
        if request.method=='PUT':
            print(request.get_json())
            npassword=request.get_json()['password']
            try:
                useremail=dndata(data)
            except Exception as e:
                print(e)
                flash('couldnot verify email')
                return redirect(url_for('newpassword',data=data))
            else:
                try:
                    cursor=mydb.cursor(buffered=True)
                    cursor.execute('update userdata set userpassword=%s where useremail=%s',[npassword,useremail])
                    mydb.commit()
                    cursor.close()
                except Exception as e:
                    print(e)
                    flash('DB connection fail unable to update password')
                    return redirect(url_for('newpassword',data=data))
                return jsonify({"message": "ok"})
        return render_template('newpassword.html',data=data)
@app.route('/addnotes',methods=['GET','POST'])
def addnotes():
    if not session.get('user'):
        flash('pls login to access dashboard features')
        return redirect(url_for('login'))
    if request.method=='POST':
        title=request.form['title']
        description=request.form['description']
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select userid from userdata where useremail=%s',[session.get('user')])
            user_id=cursor.fetchone()
            if user_id:
                cursor.execute('insert into notesdata(notestitle,notes_description,userid) values(%s,%s,%s)',[title,description,user_id[0]])
                mydb.commit()
                cursor.close()
            else:
                flash('couldnot verify user')
                return redirect(url_for('addnotes'))
        except Exception as e:
            print(e)
            flash('could not store notes details')
            return redirect(url_for('addnotes'))
        else:
            flash('notes details stored successfully')
            return redirect(url_for('addnotes'))
    return render_template('addnotes.html')
@app.route('/viewallnotes')
def viewallnotes():
    if not session.get('user'):
        flash('pls login to access dashboard features')
        return redirect(url_for('login'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select userid from userdata where useremail=%s',[session.get('user')])
        user_id=cursor.fetchone()
        if user_id:
            cursor.execute('select notesid,notestitle,created_at from notesdata where userid=%s',[user_id[0]])
            allnotesdata=cursor.fetchall() #[(1,'python notes','2026-09-12'),(2,'mysql notes','2026-09-13')]
            print(allnotesdata)
            cursor.close()
        else:
            flash('couldnot verify user')
            return redirect(url_for('dashboard'))
    except Exception as e:
        print(e)
        flash('could not fetch notes details')
        return redirect(url_for('dashboard'))
    else:
      return render_template('viewallnotes.html',allnotesdata=allnotesdata)
@app.route('/viewnotes/<nid>')
def viewnotes(nid):
    if not session.get('user'):
        flash('to access dashboard features pls login')
        return redirect(url_for('login'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select userid from userdata where useremail=%s',[session.get('user')])
        user_id=cursor.fetchone()
        if user_id:
            cursor.execute('select notesid,notestitle,notes_description,created_at from notesdata where userid=%s and notesid=%s',[user_id[0],nid])
            storednotesdata=cursor.fetchone() 
            print(storednotesdata)
            cursor.close()
        else:
            flash('couldnot verify user')
            return redirect(url_for('viewallnotes'))
    except Exception as e:
        print(e)
        flash('could not fetch notes details')
        return redirect(url_for('dashboard'))
    else:
      return render_template('viewnotes.html',storednotesdata=storednotesdata)
@app.route('/deletenotes/<nid>')
def deletenotes(nid):
    if not session.get('user'):
        flash('to access dashboard features pls login')
        return redirect(url_for('login'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select userid from userdata where useremail=%s',[session.get('user')])
        user_id=cursor.fetchone()
        if user_id:
            cursor.execute('delete from notesdata where userid=%s and notesid=%s',[user_id[0],nid])
            mydb.commit()
            cursor.close()
        else:
            flash('couldnot verify user')
            return redirect(url_for('viewallnotes'))
    except Exception as e:
        print(e)
        flash('could not delete notes details')
        return redirect(url_for('viewallnotes'))
    else:
      flash('notes deleted successfully')
      return redirect(url_for('viewallnotes'))
@app.route('/updatenotes/<nid>',methods=['GET','POST'])
def updatenotes(nid):
    if not session.get('user'):
        flash('to access dashboard features pls login')
        return redirect(url_for('login'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select userid from userdata where useremail=%s',[session.get('user')])
        user_id=cursor.fetchone()
        if user_id:
            cursor.execute('select notesid,notestitle,notes_description,created_at from notesdata where userid=%s and notesid=%s',[user_id[0],nid])
            storednotesdata=cursor.fetchone() 
            print(storednotesdata)
            cursor.close()
        else:
            flash('couldnot verify user')
            return redirect(url_for('viewallnotes'))
    except Exception as e:
        print(e)
        flash('could not fetch notes details')
        return redirect(url_for('dashboard'))
    else:
      if request.method=='POST':
          updated_title=request.form['title']
          updated_description=request.form['description']
          try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('update notesdata set notestitle=%s, notes_description=%s where userid=%s and notesid=%s',[updated_title, updated_description, user_id[0], nid])
                mydb.commit()
                cursor.close()
          except Exception as e:
                print(e)
                flash('couldnot update notes details')
                return redirect(url_for('updatenotes',nid=nid))
          else:
              flash('notes updated successfully')
              return redirect(url_for('updatenotes',nid=nid))
      return render_template('updatenotes.html',storednotesdata=storednotesdata)
@app.route('/getexceldata')
def getexceldata():
    if not session.get('user'):

        flash('pls login to access dashboard features')
        return redirect(url_for('login'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select userid from userdata where useremail=%s',[session.get('user')])
        user_id=cursor.fetchone()
        if user_id:
            cursor.execute('select notesid,notestitle,notes_description,created_at from notesdata where userid=%s',[user_id[0]])
            allnotesdata=cursor.fetchall() #[(1,'python notes','2026-09-12'),(2,'mysql notes','2026-09-13')]
            cursor.close()
        else:
            flash('couldnot verify user')
            return redirect(url_for('dashboard'))
    except Exception as e:
        print(e)
        flash('could not fetch notes details')
        
        return redirect(url_for('dashboard'))
    else:
      array_data=[list(i) for i in allnotesdata]
      columns=['NotesId','NotesTitle','Notesdesc','createdTime']
      array_data.insert(0,columns)
      return excel.make_response_from_array(array_data, 'xlsx', filename='Notesdata')
@app.route('/uploadfile',methods=['GET','POST'])
def uploadfile():
    if not session.get('user'):
        flash('pls login to access dashboard features')
        return redirect(url_for('login'))
    if request.method=='POST':
        filecontent=request.files['filedata']
        # print(filecontent)
        # print(filecontent.read())
        # print(filecontent.filename)
        fdata=filecontent.read()
        fname=filecontent.filename
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select userid from userdata where useremail=%s',[session.get('user')])
            user_id=cursor.fetchone()
            if user_id:
                cursor.execute('insert into filesdata(filename,filedata,userid) values (%s,%s,%s)',[fname,fdata,user_id[0]])
                mydb.commit()
                cursor.close()
            else:
                flash('couldnot verify user')
                return redirect(url_for('uploadfile'))
        except Exception as e:
            print(e)
            flash('could not store file data upto 4gb')
            return redirect(url_for('uploadfile'))
        else:
            flash('file uploaded successfully')
            return redirect(url_for('uploadfile'))
    return render_template('uploadfile.html')
@app.route('/viewallfiles')
def viewallfiles():
    if not session.get('user'):
        flash('pls login to access dashboard features')
        return redirect(url_for('login'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select userid from userdata where useremail=%s',[session.get('user')])
        user_id=cursor.fetchone()
        if user_id:
            cursor.execute('select fileid,filename,created_at from filesdata where userid=%s',[user_id[0]])
            allfilesdata=cursor.fetchall() #[(1,'python notes','2026-09-12'),(2,'mysql notes','2026-09-13')]
            cursor.close()
        else:
            flash('couldnot verify user')
            return redirect(url_for('dashboard'))
    except Exception as e:
        print(e)
        flash('could not fetch file details')
        return redirect(url_for('dashboard'))
    else:
      return render_template('viewallfiles.html',allfilesdata=allfilesdata)
@app.route('/viewfile/<fid>')
def viewfile(fid):
    if not session.get('user'):
        flash('pls login to access dashboard features')
        return redirect(url_for('login'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select userid from userdata where useremail=%s',[session.get('user')])
        user_id=cursor.fetchone()
        if user_id:
            cursor.execute('select fileid,filename,filedata,created_at from filesdata where userid=%s and fileid=%s',[user_id[0],fid])
            storedfiledata=cursor.fetchone() #[(1,'python notes','2026-09-12'),(2,'mysql notes','2026-09-13')]
            cursor.close()
        else:
            flash('couldnot verify user')
            return redirect(url_for('dashboard'))
    except Exception as e:
        print(e)
        flash('could not fetch file details')
        return redirect(url_for('dashboard'))
    else:
        bytes_array=BytesIO(storedfiledata[2])
        return send_file(bytes_array,as_attachment=False,download_name=storedfiledata[1])
@app.route('/downloadfile/<fid>')
def downloadfile(fid):
    if not session.get('user'):
        flash('pls login to access dashboard features')
        return redirect(url_for('login'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select userid from userdata where useremail=%s',[session.get('user')])
        user_id=cursor.fetchone()
        if user_id:
            cursor.execute('select fileid,filename,filedata,created_at from filesdata where userid=%s and fileid=%s',[user_id[0],fid])
            storedfiledata=cursor.fetchone() #[(1,'python notes','2026-09-12'),(2,'mysql notes','2026-09-13')]
            cursor.close()
        else:
            flash('couldnot verify user')
            return redirect(url_for('dashboard'))
    except Exception as e:
        print(e)
        flash('could not fetch file details')
        return redirect(url_for('dashboard'))
    else:
        bytes_array=BytesIO(storedfiledata[2])
        return send_file(bytes_array,as_attachment=True,download_name=storedfiledata[1])
@app.route('/deletefile/<fid>')
def deletefile(fid):
    if not session.get('user'):
        flash('to access dashboard features pls login')
        return redirect(url_for('login'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select userid from userdata where useremail=%s',[session.get('user')])
        user_id=cursor.fetchone()
        if user_id:
            cursor.execute('delete from filesdata where userid=%s and fileid=%s',[user_id[0],fid])
            mydb.commit()
            cursor.close()
        else:
            flash('couldnot verify user')
            return redirect(url_for('viewallfiles'))
    except Exception as e:
        print(e)
        flash('could not delete file details')
        return redirect(url_for('viewallfiles'))
    else:
      flash('file deleted successfully')
      return redirect(url_for('viewallfiles'))
@app.route('/search',methods=['POST'])
def search():
    if not session.get('user'):
        flash('pls login to access dashboard')
        return redirect(url_for('login'))
    try:
        searchdata=request.form['sdata']
        strg=['A-Za-z0-9']
        pattern=re.compile(f'^{strg}',re.IGNORECASE)
        if pattern.match(searchdata):
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('select userid from userdata where useremail=%s',[session.get('user')])
                user_id=cursor.fetchone()
                if user_id:
                    cursor.execute('select notesid,notestitle,created_at from notesdata where userid=%s and (notestitle like %s or notes_description like %s or created_at like %s)',[user_id[0],searchdata+'%',searchdata+'%',searchdata+'%'])
                    allnotesdata=cursor.fetchall()
                    cursor.close()
                else:
                    flash('Could not verify user')
                    return redirect(url_for('dashboard'))
            except Exception as e:
                print(e)
                flash('Could not fetch notesdetails')
                return redirect(url_for('dashboard'))
            else:
                return render_template('viewallnotes.html',allnotesdata=allnotesdata)
        else:
            flash('invalid search')
            return redirect(url_for('dashboard'))
    except Exception as e:
        print(e)
        flash('Something went wrong')
        return redirect(url_for('dashboard'))


  

if __name__=='__main__':
    app.run(debug=True,use_reloader=True)