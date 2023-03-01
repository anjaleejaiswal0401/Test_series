from fastapi import APIRouter,UploadFile,File
from fastapi.responses import JSONResponse
from fastapi_login import LoginManager
from fastapi.encoders import jsonable_encoder
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi import APIRouter, Request, Form, status, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi import APIRouter
# from ecom_API.pydantic_models import *
from . models import *
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from fastapi_login.exceptions import InvalidCredentialsException
from starlette.middleware.sessions import SessionMiddleware
import typing
import pandas as pd
from typing import List
import re
import psycopg2
from slugify import slugify
from datetime import datetime, timedelta

router = APIRouter()


def flash(request: Request, message: typing.Any, category: str = "") -> None:
    if "_messages" not in request.session:
        request.session["_messages"] = []
    request.session["_messages"].append(
        {"message": message, "category": category})


def get_flashed_messages(request: Request):
    print(request.session)
    return request.session.pop("_messages") if "_messages" in request.session else []


BASE_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(directory="mytestapp/templates")
templates.env.globals['get_flashed_messages'] = get_flashed_messages
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET = 'your-secret-key'
manager = LoginManager(SECRET, token_url='/auth/token')


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)



@router.get("/registration/", response_class=HTMLResponse)
async def read_item(request: Request):
    return templates.TemplateResponse("registration.html", {"request": request,})


@router.post('/registration/',)
async def create_user(request: Request, student_image: UploadFile = File(...),
                      email: EmailStr = Form(...),
                      name: str = Form(...),
                      phone: str = Form(...),
                      password: str = Form(...),
                      address: str = Form(...)):
    reg_pass = "^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!#%*?&]{6,20}$"
    pat_pass = re.compile(reg_pass)
    mat_pass = re.search(pat_pass, password)

    reg_name = re.compile('^[A-Za-z]+$')
    mat_name = re.search(reg_name, name)

    if await Register_student.filter(email=email).exists():
        flash(request, "Email already exists", "danger")
        return RedirectResponse("/registration/", status_code=status.HTTP_302_FOUND)
    elif await Register_student.filter(phone=phone).exists():
        flash(request, "Phone number already exists", "danger")
        return RedirectResponse("/registration/", status_code=status.HTTP_302_FOUND)
    else:
        if not mat_name:
            flash(request, "Your name can be in latters only ", "danger")
            return RedirectResponse("/registration/", status_code=status.HTTP_302_FOUND)
        elif len(phone) != 10:
            flash(request, "Please enter 10 digit number", "danger")
            return RedirectResponse("/registration/", status_code=status.HTTP_302_FOUND)
        elif not mat_pass:
            flash(request, "Your password lenth must be in 6 to 20 and must contain atleast one uppercase, one lower case, one special character, one number ", "danger")
            return RedirectResponse("/registration/", status_code=status.HTTP_302_FOUND)
        else:

            FILEPATH = "static/product"
            filename = student_image.filename
            extension = filename.split(".")[1]
            imagename = filename.split(".")[0]
            if extension not in ["png", "jpg", "jpeg"]:
                return {"status": "error", "detial": "File extension not allowed"}
            dt = datetime.now()
            dt_timestamp = round(datetime.timestamp(dt))
            modified_image_name = imagename+"_"+str(dt_timestamp)+"."+extension
            genrated_name2 = FILEPATH + modified_image_name
            file_content = await student_image.read()
            with open(genrated_name2, "wb") as file:
                file.write(file_content)
            file.close()

            user_obj = await Register_student.create(email=email, name=name, address=address, student_image=genrated_name2,
                                                   phone=phone, password=get_password_hash(password))
            print(user_obj)
            flash(request, "Registration successfully", "success")
            return RedirectResponse("/login/", status_code=status.HTTP_302_FOUND)

@manager.user_loader()
async def load_user(email: str):
    if await Register_student.exists(email=email):
        newapi1 = await Register_student.get(email=email)
        return newapi1

@router.get("/login/", response_class=HTMLResponse)
async def read_item(request: Request):
    return templates.TemplateResponse("login.html", {"request": request,})

@router.post('/login/', )
async def login(request: Request, email: str = Form(...),
                password: str = Form(...)):

    email = email
    user = await load_user(email)

    if not Register_student:
        flash(request, "User not exsist", "danger")
        return RedirectResponse("/login/", status_code=status.HTTP_302_FOUND)
    elif not verify_password(password, user.password):
        flash(request, "Failed to login", "danger")
        return RedirectResponse("/login/", status_code=status.HTTP_302_FOUND)
    else:
        request.session["user_id"] = user.id
        request.session["user_name"] = user.name
        request.session["user_phone"] = user.phone
        request.session["user_email"] = user.email

        print(request.session["user_id"])

        print(request.session["user_name"])
        flash(request, "Login successfully", "success")
        return RedirectResponse("/dashboard/", status_code=status.HTTP_302_FOUND)


@router.get("/", response_class=HTMLResponse)
async def read_item(request: Request):
    return templates.TemplateResponse("index.html", {"request": request,})


@router.get("/test/{id}", response_class=HTMLResponse)
async def read_item(request: Request,id:int):
    qid = await Questions.get(id =id)
    abc = await Questions.all()
    att = await Attempt.all()
    quenol=[]
    for a in att:
        quenol.append(a.queno)


    qcount = await Questions.all().count()

    return templates.TemplateResponse("test.html", {"request": request, "abc":abc, "qid":qid, "qcount":qcount,"att":att,"quenol":quenol})


@router.post("/submission/")
async def read_item(request: Request,student_id:int = Form(...),
                    submitstatus :str =Form(...),):
    studentid=request.session["user_id"]
    att = await Attempt.all()
    counts=0
    for a in att:
        if a.student_id ==studentid:
            if a.marking==1:
                counts=counts+1
    
    percentage = 100*counts/10
    await Submission.create(student_id=student_id,
                         submitstatus=submitstatus,
                         currectans=counts,
                         percentage=percentage,)
    return RedirectResponse("/ranking/", status_code=status.HTTP_302_FOUND)


@router.post("/attempt_test/")
async def read_item(request: Request,queattempt_id:int = Form(...),
                                      student_id:int = Form(...),
                                      queno :int =Form(...),
                                      ans :str = Form(...),):
    student_id=request.session["user_id"]
    qcount = await Questions.all().count()
    qid = await Questions.get(id =queno)
    if qid.answer == ans :
        mark = 1
    else:
        mark=0
    
    if queno==qcount:
        if await Attempt.filter(queno=queno).exists():
           asd =await Attempt.filter(queno=queno).update(ans=ans,marking=mark)
           return RedirectResponse(url=f"/test/{1}", status_code=303)
    
        else:
            await Attempt.create(queattempt_id=queattempt_id,
                                queno=queno,
                                ans=ans,
                                marking=mark,student_id=student_id)
            return RedirectResponse(url=f"/test/{1}", status_code=303)
    else:
        if await Attempt.filter(queno=queno).exists():
            asd =await Attempt.filter(queno=queno).update(ans=ans,marking=mark)
            return RedirectResponse(url=f"/test/{queno+1}", status_code=303)
        else:
            await Attempt.create(queattempt_id=queattempt_id,
                                    queno=queno,
                                    ans=ans,
                                    marking=mark,
                                    student_id=student_id)
        return RedirectResponse(url=f"/test/{queno+1}", status_code=303)
    
        







@router.get("/dashboard", response_class=HTMLResponse)
async def read_item(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request,})

@router.get("/ranking", response_class=HTMLResponse)
async def read_item(request: Request):
    studentid=request.session["user_id"]
    att = await Attempt.all()
    counts=0
    for a in att:
        if a.student_id ==studentid:
            counts=counts+1
    sb = await Submission.all().select_related("student")
    return templates.TemplateResponse("ranking.html", {"request": request,"att":att,"sb":sb,"counts":counts})

@router.get("/test", response_class=HTMLResponse)
async def read_item(request: Request):
    abc = await Questions.all()
    att = await Attempt.all()
    for b in abc:
        if b.id==1:
            qu=b.que
            o1=b.opt1
            o2=b.opt2
            o3=b.opt3
            o4=b.opt4
            qn=b.id
    return templates.TemplateResponse("test.html", {"request": request,"abc":abc,"qu":qu,"o1":o1,"o2":o2,"o3":o3,"o4":o4,"qn":qn,"att":att})

