from app import create_app, db
from datetime import date

from app.models import Assignment, Course, Enrollment, Material, User

app = create_app()


@app.cli.command("init-db")
def init_db():
    """Create database tables and seed demo data."""
    db.drop_all()
    db.create_all()

    admin = User(
        name="Administrador CloudLearn",
        email="admin@cloudlearn.local",
        role="admin",
        active=True,
    )
    admin.set_password("Admin123!")

    teacher = User(
        name="Docente CloudLearn",
        email="docente@cloudlearn.local",
        role="teacher",
        active=True,
    )
    teacher.set_password("Docente123!")

    student = User(
        name="Estudiante CloudLearn",
        email="estudiante@cloudlearn.local",
        role="student",
        active=True,
    )
    student.set_password("Estudiante123!")

    course = Course(
        title="Fundamentos de Computacion en la Nube",
        description="Curso introductorio sobre servicios cloud, seguridad y despliegue en Azure.",
        status="active",
        teacher=teacher,
    )

    enrollment = Enrollment(student=student, course=course, progress=35, grade=9.2)
    material = Material(
        course=course,
        created_by=teacher,
        title="Presentacion inicial de Azure",
        material_type="PDF",
        url="https://learn.microsoft.com/azure/",
    )
    assignment = Assignment(
        course=course,
        title="Actividad 1: Servicios de Azure",
        instructions="Describe tres servicios de Azure usados en CloudLearn y explica su funcion.",
        due_date=date.today(),
    )

    db.session.add_all([admin, teacher, student, course, enrollment, material, assignment])
    db.session.commit()

    print("Base de datos inicializada con usuarios y curso de prueba.")
