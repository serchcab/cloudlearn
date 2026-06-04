from functools import wraps
from datetime import date
from pathlib import Path
from uuid import uuid4

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from . import db
from .models import Assignment, Course, Enrollment, Material, Submission, User

main_bp = Blueprint("main", __name__)
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "doc", "docx", "ppt", "pptx", "txt", "zip"}


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def can_manage_course(course):
    return current_user.role == "admin" or (
        current_user.role == "teacher" and course.teacher_id == current_user.id
    )


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(file_storage):
    if not file_storage or not file_storage.filename:
        return None

    if not allowed_file(file_storage.filename):
        raise ValueError("Tipo de archivo no permitido.")

    upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)

    original_name = secure_filename(file_storage.filename)
    stored_name = f"{uuid4().hex}_{original_name}"
    file_storage.save(upload_dir / stored_name)
    return stored_name


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    stats = {
        "students": User.query.filter_by(role="student").count(),
        "teachers": User.query.filter_by(role="teacher").count(),
        "courses": Course.query.count(),
    }

    enrollments = []
    courses = []
    pending_assignments = []
    recent_submissions = []
    recent_courses = []
    report_rows = []

    if current_user.role == "student":
        enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
        submitted_assignment_ids = {
            submission.assignment_id
            for submission in Submission.query.filter_by(student_id=current_user.id).all()
        }
        course_ids = [enrollment.course_id for enrollment in enrollments]
        pending_assignments = Assignment.query.filter(
            Assignment.course_id.in_(course_ids),
            ~Assignment.id.in_(submitted_assignment_ids) if submitted_assignment_ids else True,
        ).order_by(Assignment.due_date.asc()).limit(5).all()
    elif current_user.role == "teacher":
        courses = Course.query.filter_by(teacher_id=current_user.id).all()
        course_ids = [course.id for course in courses]
        recent_submissions = Submission.query.join(Assignment).filter(
            Assignment.course_id.in_(course_ids) if course_ids else False
        ).order_by(Submission.submitted_at.desc()).limit(5).all()
    else:
        courses = Course.query.order_by(Course.created_at.desc()).all()
        recent_courses = Course.query.order_by(Course.created_at.desc()).limit(5).all()
        recent_submissions = Submission.query.order_by(Submission.submitted_at.desc()).limit(5).all()

    if current_user.role in {"admin", "teacher"}:
        managed_courses = courses if current_user.role == "teacher" else Course.query.all()
        report_rows = build_report_rows(managed_courses)

    return render_template(
        "dashboard.html",
        stats=stats,
        enrollments=enrollments,
        courses=courses,
        pending_assignments=pending_assignments,
        recent_submissions=recent_submissions,
        recent_courses=recent_courses,
        report_rows=report_rows,
    )


@main_bp.route("/admin/users", methods=["GET", "POST"])
@login_required
@role_required("admin")
def user_admin():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        role = request.form.get("role", "student")
        password = request.form.get("password", "")

        if role not in {"admin", "teacher", "student"}:
            flash("Rol no valido.", "error")
        elif not name or not email or not password:
            flash("Completa todos los campos del usuario.", "error")
        elif User.query.filter_by(email=email).first():
            flash("Ya existe un usuario con ese correo.", "error")
        else:
            user = User(name=name, email=email, role=role)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("Usuario creado correctamente.", "success")
            return redirect(url_for("main.user_admin"))

    role_filter = request.args.get("role", "")
    search = request.args.get("q", "").strip()
    users_query = User.query

    if role_filter in {"admin", "teacher", "student"}:
        users_query = users_query.filter_by(role=role_filter)

    if search:
        users_query = users_query.filter(
            db.or_(
                User.name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
            )
        )

    users = users_query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=users)


@main_bp.route("/admin/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin")
def user_edit(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        role = request.form.get("role", "student")
        password = request.form.get("password", "")
        active = request.form.get("active") == "on"
        existing_user = User.query.filter(User.email == email, User.id != user.id).first()

        if role not in {"admin", "teacher", "student"}:
            flash("Rol no valido.", "error")
        elif not name or not email:
            flash("Nombre y correo son obligatorios.", "error")
        elif existing_user:
            flash("Ya existe otro usuario con ese correo.", "error")
        else:
            user.name = name
            user.email = email
            user.role = role
            user.active = active
            if password:
                user.set_password(password)
            db.session.commit()
            flash("Usuario actualizado correctamente.", "success")
            return redirect(url_for("main.user_admin"))

    return render_template("admin/user_form.html", user=user)


def build_report_rows(courses):
    rows = []
    for course in courses:
        enrollments = course.enrollments
        grades = [enrollment.grade for enrollment in enrollments if enrollment.grade is not None]
        submissions = [
            submission
            for assignment in course.assignments
            for submission in assignment.submissions
        ]
        submission_grades = [
            submission.grade for submission in submissions if submission.grade is not None
        ]
        rows.append({
            "course": course,
            "students": len(enrollments),
            "materials": len(course.materials),
            "assignments": len(course.assignments),
            "submissions": len(submissions),
            "average_grade": round(sum(grades) / len(grades), 2) if grades else None,
            "average_submission_grade": round(sum(submission_grades) / len(submission_grades), 2) if submission_grades else None,
        })
    return rows


@main_bp.route("/reports")
@login_required
@role_required("admin", "teacher")
def reports():
    if current_user.role == "teacher":
        courses = Course.query.filter_by(teacher_id=current_user.id).order_by(Course.created_at.desc()).all()
    else:
        courses = Course.query.order_by(Course.created_at.desc()).all()

    return render_template("reports.html", report_rows=build_report_rows(courses))


@main_bp.route("/courses")
@login_required
def course_list():
    courses = Course.query.order_by(Course.created_at.desc()).all()
    return render_template("courses/list.html", courses=courses)


@main_bp.route("/courses/new", methods=["GET", "POST"])
@login_required
@role_required("admin", "teacher")
def course_new():
    teachers = User.query.filter_by(role="teacher").order_by(User.name).all()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        status = request.form.get("status", "active")
        teacher_id = request.form.get("teacher_id", type=int)

        if current_user.role == "teacher":
            teacher_id = current_user.id

        teacher = User.query.filter_by(id=teacher_id, role="teacher").first()

        if status not in {"draft", "active", "finished"}:
            flash("Estado de curso no valido.", "error")
        elif not title or not description or not teacher:
            flash("Completa los datos del curso.", "error")
        else:
            course = Course(title=title, description=description, status=status, teacher=teacher)
            db.session.add(course)
            db.session.commit()
            flash("Curso creado correctamente.", "success")
            return redirect(url_for("main.course_detail", course_id=course.id))

    return render_template("courses/form.html", teachers=teachers, course=None)


@main_bp.route("/courses/<int:course_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin", "teacher")
def course_edit(course_id):
    course = Course.query.get_or_404(course_id)
    if not can_manage_course(course):
        abort(403)

    teachers = User.query.filter_by(role="teacher").order_by(User.name).all()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        status = request.form.get("status", "active")
        teacher_id = request.form.get("teacher_id", type=int)

        if current_user.role == "teacher":
            teacher_id = current_user.id

        teacher = User.query.filter_by(id=teacher_id, role="teacher").first()

        if status not in {"draft", "active", "finished"}:
            flash("Estado de curso no valido.", "error")
        elif not title or not description or not teacher:
            flash("Completa los datos del curso.", "error")
        else:
            course.title = title
            course.description = description
            course.status = status
            course.teacher = teacher
            db.session.commit()
            flash("Curso actualizado correctamente.", "success")
            return redirect(url_for("main.course_manage", course_id=course.id))

    return render_template("courses/form.html", teachers=teachers, course=course)


@main_bp.route("/courses/<int:course_id>/delete", methods=["POST"])
@login_required
@role_required("admin", "teacher")
def course_delete(course_id):
    course = Course.query.get_or_404(course_id)
    if not can_manage_course(course):
        abort(403)

    db.session.delete(course)
    db.session.commit()
    flash("Curso eliminado correctamente.", "success")
    return redirect(url_for("main.course_list"))


@main_bp.route("/courses/<int:course_id>")
@login_required
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)

    if current_user.role == "student":
        enrollment = Enrollment.query.filter_by(
            course_id=course.id,
            student_id=current_user.id,
        ).first()
        if not enrollment:
            abort(403)

    enrollment = None
    submissions_by_assignment = {}
    if current_user.role == "student":
        enrollment = Enrollment.query.filter_by(
            course_id=course.id,
            student_id=current_user.id,
        ).first()
        submissions = Submission.query.filter_by(student_id=current_user.id).all()
        submissions_by_assignment = {
            submission.assignment_id: submission for submission in submissions
        }

    return render_template(
        "courses/detail.html",
        course=course,
        enrollment=enrollment,
        submissions_by_assignment=submissions_by_assignment,
    )


@main_bp.route("/courses/<int:course_id>/manage")
@login_required
@role_required("admin", "teacher")
def course_manage(course_id):
    course = Course.query.get_or_404(course_id)
    if not can_manage_course(course):
        abort(403)

    students = User.query.filter_by(role="student").order_by(User.name).all()
    return render_template("courses/manage.html", course=course, students=students)


@main_bp.route("/courses/<int:course_id>/enroll", methods=["POST"])
@login_required
@role_required("admin", "teacher")
def course_enroll(course_id):
    course = Course.query.get_or_404(course_id)
    if not can_manage_course(course):
        abort(403)

    student_id = request.form.get("student_id", type=int)
    student = User.query.filter_by(id=student_id, role="student").first()
    exists = Enrollment.query.filter_by(course_id=course.id, student_id=student_id).first()

    if not student:
        flash("Selecciona un estudiante valido.", "error")
    elif exists:
        flash("El estudiante ya esta inscrito en este curso.", "error")
    else:
        db.session.add(Enrollment(course=course, student=student))
        db.session.commit()
        flash("Estudiante inscrito correctamente.", "success")

    return redirect(url_for("main.course_manage", course_id=course.id))


@main_bp.route("/courses/<int:course_id>/materials", methods=["POST"])
@login_required
@role_required("admin", "teacher")
def material_new(course_id):
    course = Course.query.get_or_404(course_id)
    if not can_manage_course(course):
        abort(403)

    title = request.form.get("title", "").strip()
    material_type = request.form.get("material_type", "Documento").strip()
    url = request.form.get("url", "").strip()
    uploaded_file = request.files.get("file")

    if not title:
        flash("Agrega el titulo del material.", "error")
    else:
        try:
            stored_name = save_uploaded_file(uploaded_file)
        except ValueError as error:
            flash(str(error), "error")
            return redirect(url_for("main.course_manage", course_id=course.id))

        if not url and stored_name:
            url = url_for("main.uploaded_file", filename=stored_name)

        if not url:
            flash("Agrega un enlace o sube un archivo.", "error")
        else:
            material = Material(
                course=course,
                created_by=current_user,
                title=title,
                material_type=material_type or "Documento",
                url=url,
                file_name=stored_name,
            )
            db.session.add(material)
            db.session.commit()
            flash("Material agregado correctamente.", "success")

    return redirect(url_for("main.course_manage", course_id=course.id))


@main_bp.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


@main_bp.route("/materials/<int:material_id>/delete", methods=["POST"])
@login_required
@role_required("admin", "teacher")
def material_delete(material_id):
    material = Material.query.get_or_404(material_id)
    course = material.course
    if not can_manage_course(course):
        abort(403)

    db.session.delete(material)
    db.session.commit()
    flash("Material eliminado correctamente.", "success")
    return redirect(url_for("main.course_manage", course_id=course.id))


@main_bp.route("/courses/<int:course_id>/assignments", methods=["POST"])
@login_required
@role_required("admin", "teacher")
def assignment_new(course_id):
    course = Course.query.get_or_404(course_id)
    if not can_manage_course(course):
        abort(403)

    title = request.form.get("title", "").strip()
    instructions = request.form.get("instructions", "").strip()
    due_date_value = request.form.get("due_date") or None
    due_date = date.fromisoformat(due_date_value) if due_date_value else None

    if not title or not instructions:
        flash("Agrega titulo e instrucciones para la tarea.", "error")
    else:
        assignment = Assignment(
            course=course,
            title=title,
            instructions=instructions,
            due_date=due_date,
        )
        db.session.add(assignment)
        db.session.commit()
        flash("Tarea creada correctamente.", "success")

    return redirect(url_for("main.course_manage", course_id=course.id))


@main_bp.route("/assignments/<int:assignment_id>/submit", methods=["POST"])
@login_required
@role_required("student")
def assignment_submit(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    enrollment = Enrollment.query.filter_by(
        course_id=assignment.course_id,
        student_id=current_user.id,
    ).first()

    if not enrollment:
        abort(403)

    answer = request.form.get("answer", "").strip()
    if not answer:
        flash("Escribe tu respuesta antes de entregar.", "error")
    else:
        submission = Submission.query.filter_by(
            assignment_id=assignment.id,
            student_id=current_user.id,
        ).first()

        if submission:
            submission.answer = answer
        else:
            submission = Submission(
                assignment=assignment,
                student=current_user,
                answer=answer,
            )
            db.session.add(submission)

        db.session.commit()
        flash("Tarea entregada correctamente.", "success")

    return redirect(url_for("main.course_detail", course_id=assignment.course_id))


@main_bp.route("/submissions/<int:submission_id>/grade", methods=["POST"])
@login_required
@role_required("admin", "teacher")
def submission_grade(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    if not can_manage_course(submission.assignment.course):
        abort(403)

    grade = request.form.get("grade", type=float)
    feedback = request.form.get("feedback", "").strip()

    if grade is None or grade < 0 or grade > 10:
        flash("La calificacion debe estar entre 0 y 10.", "error")
    else:
        submission.grade = grade
        submission.feedback = feedback
        db.session.commit()
        flash("Entrega calificada correctamente.", "success")

    return redirect(url_for("main.course_manage", course_id=submission.assignment.course_id))


@main_bp.route("/enrollments/<int:enrollment_id>/grade", methods=["POST"])
@login_required
@role_required("admin", "teacher")
def enrollment_grade(enrollment_id):
    enrollment = Enrollment.query.get_or_404(enrollment_id)
    if not can_manage_course(enrollment.course):
        abort(403)

    progress = request.form.get("progress", type=int)
    grade = request.form.get("grade", type=float)

    if progress is None or progress < 0 or progress > 100:
        flash("El avance debe estar entre 0 y 100.", "error")
    else:
        enrollment.progress = progress
        enrollment.grade = grade
        db.session.commit()
        flash("Calificacion actualizada.", "success")

    return redirect(url_for("main.course_manage", course_id=enrollment.course_id))
