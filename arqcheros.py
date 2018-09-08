# -*- encoding: utf-8 -*-
import os
import os.path as op

from flask import Flask, url_for, redirect, render_template, request

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, Unicode, ForeignKey
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql.expression import func
from sqlalchemy import cast, Float

from wtforms import form, fields, validators, widgets, SelectMultipleField

import flask_admin as admin
from flask_admin import form as formadmin

from flask_admin import helpers, expose
from flask_admin.contrib import sqla
from flask_admin.contrib.sqla import filters

import flask_login as login
from flask_login import login_required

from werkzeug.security import generate_password_hash, check_password_hash

from jinja2 import Markup

import numpy as np
import enum

# Create Flask application
app = Flask(__name__)

# Create dummy secrey key so we can use sessions
app.config['SECRET_KEY'] = '123456790'

# Create in-memory database
app.config['DATABASE_FILE'] = 'sample_db.sqlite'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + app.config['DATABASE_FILE']
app.config['SQLALCHEMY_ECHO'] = True
db = SQLAlchemy(app)

# Create directory for file fields to use
file_path = op.join(op.dirname(__file__), 'static')
try:
    os.mkdir(file_path)
except OSError:
    pass

# Initialize flask-login
def init_login():
    login_manager = login.LoginManager()
    login_manager.init_app(app)

    # Create user loader function
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.query(User).get(user_id)

# Flask views
@app.route('/')
def index():
    return render_template('index.html')


# Initialize flask-login
init_login()

# Create user model.
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    login = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120))
    password = db.Column(db.String(64))

    # Flask-Login integration
    # NOTE: is_authenticated, is_active, and is_anonymous
    # are methods in Flask-Login < 0.3.0
    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    # Required for administrative interface
    def __str__(self):
        return self.login

# Define login and registration forms (for flask-login)
class LoginForm(form.Form):
    login = fields.StringField(validators=[validators.required()])
    password = fields.PasswordField(validators=[validators.required()])

    def validate_login(self, field):
        user = self.get_user()

        if user is None:
            raise validators.ValidationError('Invalid user')

        # we're comparing the plaintext pw with the the hash from the db
        if not check_password_hash(user.password, self.password.data):
        # to compare plain text passwords use
        # if user.password != self.password.data:
            raise validators.ValidationError('Invalid password')

    def get_user(self):
        return db.session.query(User).filter_by(login=self.login.data).first()


class RegistrationForm(form.Form):
    login = fields.StringField(validators=[validators.required()])
    email = fields.StringField()
    password = fields.PasswordField(validators=[validators.required()])

    def validate_login(self, field):
        if db.session.query(User).filter_by(login=self.login.data).count() > 0:
            raise validators.ValidationError('Duplicate username')

# Create useful functions
def clasificacion_tamano(dato):
    tamanos = [0, 20, 40, 60, 80, 120, 160]
    clasificacion = ['Tamano 1: Muy pequeno', 'Tamano 1: Pequeno', 'Tamano 2: Mediano pequeno', 'Tamano 2: Mediano grande', 'Tamano 3: Grande', 'Tamano 3: Muy grande', 'Tamano 4: Grandísimo']
    tamanos.reverse()
    clasificacion.reverse()

    tamano_clasificacion = [(i, j) for i, j in zip(tamanos, clasificacion)]
    for i, j in tamano_clasificacion:
        if dato >= i:
            return j

def modulo_largo_ancho(pendiente):
    modulos = [0, 1/2, 3/4, 1, 3/2, 2, 3, 6]
    clasificacion = ['H: Cortísimo o corto anchísimo',
                     'G: Lasca muy ancha o corto ancho',
                     'F: Lasca ancha o corto ancho',
                     'E: Lasca o laminar normal o mediana normal',
                     'D: Lasca o laminar mediano alargada',
                     'C: Lámina o laminar normal',
                     'B: Lámina o laminar angosto',
                     'A: Lámina o laminar muy angosto']
    modulos.reverse()
    clasificacion.reverse()

    modulo_clasificacion = [(i, j) for i, j in zip(modulos, clasificacion)]
    for i, j in modulo_clasificacion:
        if pendiente >= i:
            return j

def modulo_ancho_espesor(a_e):
    if a_e < 1.5:
        return 'Muy grueso / muy espeso'
    elif a_e <= 3:
        return 'Grueso / espeso'
    else:
        return 'Otro (' + str(a_e) + ')'

# Create useful data structures

Subgrupos = enum.Enum("Grupos y subgrupos", [
("Tajadores (Chopper) con filo de sección asimétrica: Cóncavo (Lateral, frontal)","Tajadores_Chopper_con_filo_de_sección_asimétrica_Cóncavo_Lateral_frontal"),
("Tajadores (Chopper) con filo de sección asimétrica: Convexo (Lateral, frontal)","Tajadores_Chopper_con_filo_de_sección_asimétrica_Convexo_Lateral_frontal"),
("Tajadores (Chopper) con filo de sección asimétrica: Fragmentos no diferenciados","Tajadores_Chopper_con_filo_de_sección_asimétrica_Fragmentos_no_diferenciados"),
("Unifaces: con arista sinuosa irregular","Unifaces_con_arista_sinuosa_irregular"),
("Unifaces: con arista sinuosa regularizada","Unifaces_con_arista_sinuosa_regularizada"),
("Unifaces: fragmentos no diferenciados","Unifaces_fragmentos_no_diferenciados"),
("Bifaces:  con arista sinuosa irregular","Bifaces_con_arista_sinuosa_irregular"),
("Bifaces:  con arista sinuosa regularizada","Bifaces_con_arista_sinuosa_regularizada"),
("Bifaces:  fragmentos no diferenciados","Bifaces_fragmentos_no_diferenciados"),
("Piezas foliaceas: con arista sinuosa irregular","Piezas_foliaceas_con_arista_sinuosa_irregular"),
("Piezas foliaceas: con arista sinuosa regularizada","Piezas_foliaceas_con_arista_sinuosa_regularizada"),
("Piezas foliaceas: fragmentos no diferenciados","Piezas_foliaceas_fragmentos_no_diferenciados"),
("Filos largos de arista sinuosa, bisel simétrico o asimétrico bifacial: Recto (Lateral, frontal)","Filos_largos_de_arista_sinuosa_bisel_simétrico_o_asimétrico_bifacial_Recto_Lateral_frontal"),
("Filos largos de arista sinuosa, bisel simétrico o asimétrico bifacial: Cóncavo (Lateral, frontal)","Filos_largos_de_arista_sinuosa_bisel_simétrico_o_asimétrico_bifacial_Cóncavo_Lateral_frontal"),
("Filos largos de arista sinuosa, bisel simétrico o asimétrico bifacial: Convexo (Lateral, frontal)","Filos_largos_de_arista_sinuosa_bisel_simétrico_o_asimétrico_bifacial_Convexo_Lateral_frontal"),
("Filos largos de arista sinuosa, bisel simétrico o asimétrico bifacial: Fragmento no diferenciado","Filos_largos_de_arista_sinuosa_bisel_simétrico_o_asimétrico_bifacial_Fragmento_no_diferenciado"),
("Picos, artefactos de retalla extendida, bifacial o unifacial, de tamano muy grande o grandísimo, con extremo distal en punta de sección triédrica o romboidal muy gruesa: con arista sinuosa irregular","Picos_artefactos_de_retalla_extendida_bifacial_o_unifacial_de_tamano_muy_grande_o_grandísimo_con_extremo_distal_en_punta_de_sección_triédrica_o_romboidal_muy_gruesa_con_arista_sinuosa_irregular"),
("Picos, artefactos de retalla extendida, bifacial o unifacial, de tamano muy grande o grandísimo, con extremo distal en punta de sección triédrica o romboidal muy gruesa: con arista sinuosa regularizada","Picos_artefactos_de_retalla_extendida_bifacial_o_unifacial_de_tamano_muy_grande_o_grandísimo_con_extremo_distal_en_punta_de_sección_triédrica_o_romboidal_muy_gruesa_con_arista_sinuosa_regularizada"),
("Picos, artefactos de retalla extendida, bifacial o unifacial, de tamano muy grande o grandísimo, con extremo distal en punta de sección triédrica o romboidal muy gruesa: fragmentos no diferenciados","Picos_artefactos_de_retalla_extendida_bifacial_o_unifacial_de_tamano_muy_grande_o_grandísimo_con_extremo_distal_en_punta_de_sección_triédrica_o_romboidal_muy_gruesa_fragmentos_no_diferenciados"),
("Palas: lajas o lascas muy grandes o grandísimas, con filo transversal de retalla y/o retoque marginal o periférico;sector de prehensión o enmangue esbozado, destacado o diferenciado","Palas_lajas_o_lascas_muy_grandes_o_grandísimas_con_filo_transversal_de_retalla_y/o_retoque_marginal_o_periférico;sector_de_prehensión_o_enmangue_esbozado_destacado_o_diferenciado"),
("Cepillos (Rabot): Filo largo convexo (Lateral, frontal)","Cepillos_Rabot_Filo_largo_convexo_Lateral_frontal"),
("Cepillos (Rabot): Filo largo recto (lateral, frontal)","Cepillos_Rabot_Filo_largo_recto_lateral_frontal"),
("Cepillos (Rabot): Filo corto convexo (Lateral, frontal)","Cepillos_Rabot_Filo_corto_convexo_Lateral_frontal"),
("Cepillos (Rabot): Filo corto recto (idem.)","Cepillos_Rabot_Filo_corto_recto_idem."),
("Cepillos (Rabot): Filo restringido convexo (Lateral, frontal)","Cepillos_Rabot_Filo_restringido_convexo_Lateral_frontal"),
("Cepillos (Rabot): Filo restringido  recto (Lateral, frontal)","Cepillos_Rabot_Filo_restringido_recto_Lateral_frontal"),
("Cepillos (Rabot): Fragmentos no diferenciados","Cepillos_Rabot_Fragmentos_no_diferenciados"),
("Raspadores: de filo corto (Lateral, frontal)","Raspadores_de_filo_corto_Lateral_frontal"),
("Raspadores: de filo restringido (Lateral, frontal, angular)","Raspadores_de_filo_restringido_Lateral_frontal_angular"),
("Raspadores: de filo largo (Lateral, frontal)","Raspadores_de_filo_largo_Lateral_frontal"),
("Raspadores: de filo extendido (Fronto-lateral, fronto-bilateral)","Raspadores_de_filo_extendido_Fronto-lateral_fronto-bilateral"),
("Raspadores: de filo perimetral","Raspadores_de_filo_perimetral"),
("Raspadores: fragmentos no diferenciados","Raspadores_fragmentos_no_diferenciados"),
("Raclettes (filo asimétrico, abrupto u oblicuo, de microret.ultramarg.):  de filo corto (Lateral, frontal)","Raclettes_filo_asimétrico_abrupto_u_oblicuo_de_microret.ultramarg._de_filo_corto_Lateral_frontal"),
("Raclettes (filo asimétrico, abrupto u oblicuo, de microret.ultramarg.):  de filo restringido (Lateral, frontal, angular)","Raclettes_filo_asimétrico_abrupto_u_oblicuo_de_microret.ultramarg._de_filo_restringido_Lateral_frontal_angular"),
("Raclettes (filo asimétrico, abrupto u oblicuo, de microret.ultramarg.):  de filo largo (Lateral, frontal)","Raclettes_filo_asimétrico_abrupto_u_oblicuo_de_microret.ultramarg._de_filo_largo_Lateral_frontal"),
("Raclettes (filo asimétrico, abrupto u oblicuo, de microret.ultramarg.):  de filo extendido (Fronto-lateral, fronto-bilateral)","Raclettes_filo_asimétrico_abrupto_u_oblicuo_de_microret.ultramarg._de_filo_extendido_Fronto-lateral_fronto-bilateral"),
("Raclettes (filo asimétrico, abrupto u oblicuo, de microret.ultramarg.):  fragmentos no diferenciados","Raclettes_filo_asimétrico_abrupto_u_oblicuo_de_microret.ultramarg._fragmentos_no_diferenciados"),
("Raederas. Artefactos de filos largos, de bisel unifacial o bifacial, con sección asimétricay ángulos de filo ≥ a 50º: de filo convexo(Lateral, frontal)","Raederas._Artefactos_de_filos_largos_de_bisel_unifacial_o_bifacial_con_sección_asimétricay_ángulos_de_filo_≥_a_50º_de_filo_convexo(Lateral_frontal"),
("Raederas. Artefactos de filos largos, de bisel unifacial o bifacial, con sección asimétricay ángulos de filo ≥ a 50º: de filo recto (Lateral, frontal)","Raederas._Artefactos_de_filos_largos_de_bisel_unifacial_o_bifacial_con_sección_asimétricay_ángulos_de_filo_≥_a_50º_de_filo_recto_Lateral_frontal"),
("Raederas. Artefactos de filos largos, de bisel unifacial o bifacial, con sección asimétricay ángulos de filo ≥ a 50º: de filo concavo (Lateral, frontal)","Raederas._Artefactos_de_filos_largos_de_bisel_unifacial_o_bifacial_con_sección_asimétricay_ángulos_de_filo_≥_a_50º_de_filo_concavo_Lateral_frontal"),
("Raederas. Artefactos de filos largos, de bisel unifacial o bifacial, con sección asimétricay ángulos de filo ≥ a 50º: de filos convergentes en apice romo","Raederas._Artefactos_de_filos_largos_de_bisel_unifacial_o_bifacial_con_sección_asimétricay_ángulos_de_filo_≥_a_50º_de_filos_convergentes_en_apice_romo"),
("Raederas. Artefactos de filos largos, de bisel unifacial o bifacial, con sección asimétricay ángulos de filo ≥ a 50º: de filos convergentes en punta","Raederas._Artefactos_de_filos_largos_de_bisel_unifacial_o_bifacial_con_sección_asimétricay_ángulos_de_filo_≥_a_50º_de_filos_convergentes_en_punta"),
("Raederas. Artefactos de filos largos, de bisel unifacial o bifacial, con sección asimétricay ángulos de filo ≥ a 50º: Fragmentos no diferenciado","Raederas._Artefactos_de_filos_largos_de_bisel_unifacial_o_bifacial_con_sección_asimétricay_ángulos_de_filo_≥_a_50º_Fragmentos_no_diferenciado"),
("Laminas retocadas: de filo convexo","Laminas_retocadas_de_filo_convexo"),
("Laminas retocadas: de filo recto","Laminas_retocadas_de_filo_recto"),
("Laminas retocadas: de filo concavo","Laminas_retocadas_de_filo_concavo"),
("Laminas retocadas: de filos convergentes en apice romo","Laminas_retocadas_de_filos_convergentes_en_apice_romo"),
("Laminas retocadas: de filos convergentes en punta","Laminas_retocadas_de_filos_convergentes_en_punta"),
("Laminas retocadas: de filos recto/concavos con escotaduras contrapuestas [Láminas estranguladas]","Laminas_retocadas_de_filos_recto/concavos_con_escotaduras_contrapuestas_Láminas_estranguladas"),
("Laminas retocadas: fragmentos no diferenciados","Laminas_retocadas_fragmentos_no_diferenciados"),
("Raederas-raspadores (Limaces) .Artefactos con filo perimetral en bisel obicuo o abrupto, sección asimétrica y módulo laminar","Raederas-raspadores_Limaces_.Artefactos_con_filo_perimetral_en_bisel_obicuo_o_abrupto_sección_asimétrica_y_módulo_laminar"),
("Cuchillos de filo formatizado: de filo convexo(Lateral, frontal)","Cuchillos_de_filo_formatizado_de_filo_convexo(Lateral_frontal"),
("Cuchillos de filo formatizado: de filo recto (Lateral, frontal)","Cuchillos_de_filo_formatizado_de_filo_recto_Lateral_frontal"),
("Cuchillos de filo formatizado: de filo concavo (Lateral, frontal)","Cuchillos_de_filo_formatizado_de_filo_concavo_Lateral_frontal"),
("Cuchillos de filo formatizado: de filos convergentes en apice romo","Cuchillos_de_filo_formatizado_de_filos_convergentes_en_apice_romo"),
("Cuchillos de filo formatizado: de filos convergentes en punta","Cuchillos_de_filo_formatizado_de_filos_convergentes_en_punta"),
("Cuchillos de filo formatizado: fragmentos no diferenciados","Cuchillos_de_filo_formatizado_fragmentos_no_diferenciados"),
("Cuchillos de filo natural con dorso formatizado: de filo convexo(Lateral, frontal)","Cuchillos_de_filo_natural_con_dorso_formatizado_de_filo_convexo(Lateral_frontal"),
("Cuchillos de filo natural con dorso formatizado: de filo recto (Lateral, frontal)","Cuchillos_de_filo_natural_con_dorso_formatizado_de_filo_recto_Lateral_frontal"),
("Cuchillos de filo natural con dorso formatizado: de filo concavo (Lateral, frontal)","Cuchillos_de_filo_natural_con_dorso_formatizado_de_filo_concavo_Lateral_frontal"),
("Cuchillos de filo natural con dorso formatizado: fragmentos no diferenciados","Cuchillos_de_filo_natural_con_dorso_formatizado_fragmentos_no_diferenciados"),
("Cortantes (trinchetas). Artefactos de filo corto o restringido de sección asimétrica con angulos menores a 50º o de sección simétrica -de bisel simple o doble-. Excepcion: tamanos pequenos o medianos pequenos con filo perimetral o largo: de filo convexo (Lateral, frontal o angular)","Cortantes_trinchetas)._Artefactos_de_filo_corto_o_restringido_de_sección_asimétrica_con_angulos_menores_a_50º_o_de_sección_simétrica_-de_bisel_simple_o_doble-._Excepcion_tamanos_pequenos_o_medianos_pequenos_con_filo_perimetral_o_largo_de_filo_convexo_Lateral_frontal_o_angular"),
("Cortantes (trinchetas). Artefactos de filo corto o restringido de sección asimétrica con angulos menores a 50º o de sección simétrica -de bisel simple o doble-. Excepcion: tamanos pequenos o medianos pequenos con filo perimetral o largo: de filo recto (Lateral, frontal o angular)","Cortantes_trinchetas)._Artefactos_de_filo_corto_o_restringido_de_sección_asimétrica_con_angulos_menores_a_50º_o_de_sección_simétrica_-de_bisel_simple_o_doble-._Excepcion_tamanos_pequenos_o_medianos_pequenos_con_filo_perimetral_o_largo_de_filo_recto_Lateral_frontal_o_angular"),
("Cortantes (trinchetas). Artefactos de filo corto o restringido de sección asimétrica con angulos menores a 50º o de sección simétrica -de bisel simple o doble-. Excepcion: tamanos pequenos o medianos pequenos con filo perimetral o largo: de filos convergentes en apice romo","Cortantes_trinchetas)._Artefactos_de_filo_corto_o_restringido_de_sección_asimétrica_con_angulos_menores_a_50º_o_de_sección_simétrica_-de_bisel_simple_o_doble-._Excepcion_tamanos_pequenos_o_medianos_pequenos_con_filo_perimetral_o_largo_de_filos_convergentes_en_apice_romo"),
("Cortantes (trinchetas). Artefactos de filo corto o restringido de sección asimétrica con angulos menores a 50º o de sección simétrica -de bisel simple o doble-. Excepcion: tamanos pequenos o medianos pequenos con filo perimetral o largo: de filos convergentes en punta","Cortantes_trinchetas)._Artefactos_de_filo_corto_o_restringido_de_sección_asimétrica_con_angulos_menores_a_50º_o_de_sección_simétrica_-de_bisel_simple_o_doble-._Excepcion_tamanos_pequenos_o_medianos_pequenos_con_filo_perimetral_o_largo_de_filos_convergentes_en_punta"),
("Cortantes (trinchetas). Artefactos de filo corto o restringido de sección asimétrica con angulos menores a 50º o de sección simétrica -de bisel simple o doble-. Excepcion: tamanos pequenos o medianos pequenos con filo perimetral o largo: fragmentos no diferenciados","Cortantes_trinchetas)._Artefactos_de_filo_corto_o_restringido_de_sección_asimétrica_con_angulos_menores_a_50º_o_de_sección_simétrica_-de_bisel_simple_o_doble-._Excepcion_tamanos_pequenos_o_medianos_pequenos_con_filo_perimetral_o_largo_fragmentos_no_diferenciados"),
("Grupo de las cunas, gubias y escoplos 	sección simétrica o asimétrica: Cuna (filo corto de bisel simetrico, convexo o recto)","Grupo_de_las_cunas_gubias_y_escoplos_	sección_simétrica_o_asimétrica_Cuna_filo_corto_de_bisel_simetrico_convexo_o_recto"),
("Grupo de las cunas, gubias y escoplos 	sección simétrica o asimétrica: Gubia (arista cóncavilínea en norma sagital o lateral,simet.ó asim., recta o cóncava)","Grupo_de_las_cunas_gubias_y_escoplos_	sección_simétrica_o_asimétrica_Gubia_arista_cóncavilínea_en_norma_sagital_o_lateral,simet.ó_asim._recta_o_cóncava"),
("Grupo de las cunas, gubias y escoplos 	sección simétrica o asimétrica: Escoplo (filos rectos, bisel asimétrico)","Grupo_de_las_cunas_gubias_y_escoplos_	sección_simétrica_o_asimétrica_Escoplo_filos_rectos_bisel_asimétrico"),
("Grupo de las cunas, gubias y escoplos 	sección simétrica o asimétrica: fragmentos no diferenciados","Grupo_de_las_cunas_gubias_y_escoplos_	sección_simétrica_o_asimétrica_fragmentos_no_diferenciados"),
("Muescas: retocada o microrretocada","Muescas_retocada_o_microrretocada"),
("Muescas: de lascado simple","Muescas_de_lascado_simple"),
("Raspadores-denticulados: de filo corto (Lateral, frontal)","Raspadores-denticulados_de_filo_corto_Lateral_frontal"),
("Raspadores-denticulados: de filo restringido (Lateral, frontal, angular)","Raspadores-denticulados_de_filo_restringido_Lateral_frontal_angular"),
("Raspadores-denticulados: de filo largo (Lateral, frontal)","Raspadores-denticulados_de_filo_largo_Lateral_frontal"),
("Raspadores-denticulados: de filo extendido (Fronto-lateral, fronto-bilateral)","Raspadores-denticulados_de_filo_extendido_Fronto-lateral_fronto-bilateral"),
("Raspadores-denticulados: de filo perimetral","Raspadores-denticulados_de_filo_perimetral"),
("Raspadores-denticulados: fragmentos no diferenciados","Raspadores-denticulados_fragmentos_no_diferenciados"),
("Cuchillos-denticulados: de filo convexo (Lateral, frontal o angular)","Cuchillos-denticulados_de_filo_convexo_Lateral_frontal_o_angular"),
("Cuchillos-denticulados: de filo recto (Lateral, frontal o angular)","Cuchillos-denticulados_de_filo_recto_Lateral_frontal_o_angular"),
("Cuchillos-denticulados: de filos convergentes en apice romo","Cuchillos-denticulados_de_filos_convergentes_en_apice_romo"),
("Cuchillos-denticulados: de filos convergentes en punta","Cuchillos-denticulados_de_filos_convergentes_en_punta"),
("Cuchillos-denticulados: fragmentos no diferenciados","Cuchillos-denticulados_fragmentos_no_diferenciados"),
("Cortantes-denticulados: de filo restringido (Lateral, frontal, angular)","Cortantes-denticulados_de_filo_restringido_Lateral_frontal_angular"),
("Cortantes-denticulados: de filo corto menor a 2 cm ","Cortantes-denticulados_de_filo_corto_menor_a_2_cm_"),
("Cortantes-denticulados: de filo largo de 3cm o menor (Lateral, frontal)","Cortantes-denticulados_de_filo_largo_de_3cm_o_menor_Lateral_frontal"),
("Cortantes-denticulados: de filo extendido en piezas menores a 3cm. (Fronto-lateral, fronto-bilateral)","Cortantes-denticulados_de_filo_extendido_en_piezas_menores_a_3cm._Fronto-lateral_fronto-bilateral"),
("Cortantes-denticulados: de filo perrimetral, en piezas menores a 3cm de long.o ancho máximo.","Cortantes-denticulados_de_filo_perrimetral_en_piezas_menores_a_3cm_de_long.o_ancho_máximo."),
("Cepillos-denticulados: de filo corto (Lateral, frontal)","Cepillos-denticulados_de_filo_corto_Lateral_frontal"),
("Cepillos-denticulados: de filo restringido (Lateral, frontal, angular)","Cepillos-denticulados_de_filo_restringido_Lateral_frontal_angular"),
("Cepillos-denticulados: de filo largo (Lateral, frontal)","Cepillos-denticulados_de_filo_largo_Lateral_frontal"),
("Cepillos-denticulados: de filo extendido (Fronto-lateral, fronto-bilateral)","Cepillos-denticulados_de_filo_extendido_Fronto-lateral_fronto-bilateral"),
("Cepillos-denticulados: de filo perimetral","Cepillos-denticulados_de_filo_perimetral"),
("Cepillos-denticulados: fragmentos no diferenciados","Cepillos-denticulados_fragmentos_no_diferenciados"),
("Puntas entre muescas:  Grupo de los artefactos burilantes","Puntas_entre_muescas_Grupo_de_los_artefactos_burilantes"),
("Puntas entre muescas: Punta burilante simple","Puntas_entre_muescas_Punta_burilante_simple"),
("Puntas entre muescas: Punta burilante de arista oblicua","Puntas_entre_muescas_Punta_burilante_de_arista_oblicua"),
("Puntas entre muescas: Muesca burilante","Puntas_entre_muescas_Muesca_burilante"),
("Puntas entre muescas: Buril","Puntas_entre_muescas_Buril"),
("Perforadores: Punta de sección asimetrica (axial,angular), base de prehensión o enmangue format.","Perforadores_Punta_de_sección_asimetrica_axial,angular_base_de_prehensión_o_enmangue_format."),
("Perforadores: Punta de sección asimétrica (axial,angular), base de prehensión o enmangue no formatizado.","Perforadores_Punta_de_sección_asimétrica_axial,angular_base_de_prehensión_o_enmangue_no_formatizado."),
("Perforadores: Punta de sección simétrica (axial,angular), base de prehensión o enmangue formatizado","Perforadores_Punta_de_sección_simétrica_axial,angular_base_de_prehensión_o_enmangue_formatizado"),
("Perforadores: Punta de sección simétrica (axial,angular), base de prehensión o enmangue no formatizado","Perforadores_Punta_de_sección_simétrica_axial,angular_base_de_prehensión_o_enmangue_no_formatizado"),
("Perforadores: Fragmentos no diferenciados","Perforadores_Fragmentos_no_diferenciados"),
("Puntas de proyectil (cabezales líticos): Apedunculada (forma geométrica del limbo) con aletas","Puntas_de_proyectil_cabezales_líticos_Apedunculada_forma_geométrica_del_limbo_con_aletas"),
("Puntas de proyectil (cabezales líticos): Apedunculada (forma geom.del limbo) sin aletas","Puntas_de_proyectil_cabezales_líticos_Apedunculada_forma_geom.del_limbo_sin_aletas"),
("Puntas de proyectil (cabezales líticos): Preforma de punta apedunculada","Puntas_de_proyectil_cabezales_líticos_Preforma_de_punta_apedunculada"),
("Puntas de proyectil (cabezales líticos): Fragmento proximal de punta apedunculada","Puntas_de_proyectil_cabezales_líticos_Fragmento_proximal_de_punta_apedunculada"),
("Puntas de proyectil (cabezales líticos): Pedúnculo esbozado, limbo (forma geom.) con hombros y/o aletas","Puntas_de_proyectil_cabezales_líticos_Pedúnculo_esbozado_limbo_forma_geom._con_hombros_y/o_aletas"),
("Puntas de proyectil (cabezales líticos): Pedúnculo esbozado, limbo (forma geom.) sin hombros y/o aletas","Puntas_de_proyectil_cabezales_líticos_Pedúnculo_esbozado_limbo_forma_geom._sin_hombros_y/o_aletas"),
("Puntas de proyectil (cabezales líticos): Pedúnculo destacado, limbo (forma geom.) con hombros y/o aletas","Puntas_de_proyectil_cabezales_líticos_Pedúnculo_destacado_limbo_forma_geom._con_hombros_y/o_aletas"),
("Puntas de proyectil (cabezales líticos): Pedúnculo destacado, limbo (forma geom.) sin hombros y/o aletas","Puntas_de_proyectil_cabezales_líticos_Pedúnculo_destacado_limbo_forma_geom._sin_hombros_y/o_aletas"),
("Puntas de proyectil (cabezales líticos): Pedúnculo diferenciado,  limbo (forma geom.) con hombros y/o aletas","Puntas_de_proyectil_cabezales_líticos_Pedúnculo_diferenciado_limbo_forma_geom._con_hombros_y/o_aletas"),
("Perforadores: Apedunculada (forma geométrica del limbo) con aletas","Perforadores_Apedunculada_forma_geométrica_del_limbo_con_aletas"),
("Perforadores: Apedunculada (forma geom.del limbo) sin aletas","Perforadores_Apedunculada_forma_geom.del_limbo_sin_aletas"),
("Perforadores: Preforma de punta apedunculada","Perforadores_Preforma_de_punta_apedunculada"),
("Perforadores: Fragmento proximal de punta apedunculada","Perforadores_Fragmento_proximal_de_punta_apedunculada"),
("Perforadores: Pedúnculo esbozado, limbo (forma geom.) con hombros y/o aletas","Perforadores_Pedúnculo_esbozado_limbo_forma_geom._con_hombros_y/o_aletas"),
("Perforadores: Pedúnculo esbozado, limbo (forma geom.) sin hombros y/o aletas","Perforadores_Pedúnculo_esbozado_limbo_forma_geom._sin_hombros_y/o_aletas"),
("Perforadores: Pedúnculo destacado, limbo (forma geom.) con hombros y/o aletas","Perforadores_Pedúnculo_destacado_limbo_forma_geom._con_hombros_y/o_aletas"),
("Perforadores: Pedúnculo destacado, limbo (forma geom.) sin hombros y/o aletas","Perforadores_Pedúnculo_destacado_limbo_forma_geom._sin_hombros_y/o_aletas"),
("Perforadores: Pedúnculo diferenciado,  limbo (forma geom.) con hombros y/o aletas","Perforadores_Pedúnculo_diferenciado_limbo_forma_geom._con_hombros_y/o_aletas"),
("Perforadores: Pedúnculo diferenciado,  limbo (forma geom.) sin hombros y/o aletas","Perforadores_Pedúnculo_diferenciado_limbo_forma_geom._sin_hombros_y/o_aletas"),
("Perforadores: Preforma de punta pedunculada","Perforadores_Preforma_de_punta_pedunculada"),
("Perforadores: Fragmento proximal de pedunculo","Perforadores_Fragmento_proximal_de_pedunculo"),
("Perforadores: Fragmento de pedúnculo","Perforadores_Fragmento_de_pedúnculo"),
("Perforadores: Fragmento distal y/o ápice de limbo","Perforadores_Fragmento_distal_y/o_ápice_de_limbo"),
("Perforadores: Fragmento mesial de limbo","Perforadores_Fragmento_mesial_de_limbo"),
("Artefactos apedunculados o pedunculados de limbo embotado","Artefactos_apedunculados_o_pedunculados_de_limbo_embotado"),
("Artefactos o fragmentos  de artefactos con formatización sumaria","Artefactos_o_fragmentos_de_artefactos_con_formatización_sumaria"),
("Fragmentos no diferenciados de piezas formatizadas","Fragmentos_no_diferenciados_de_piezas_formatizadas"),
("Fragmentos no diferenciados de filos o puntas formatizadas","Fragmentos_no_diferenciados_de_filos_o_puntas_formatizadas"),
("Filos naturales de lascas u hojas con rastros complementarios","Filos_naturales_de_lascas_u_hojas_con_rastros_complementarios"),
("Puntas naturales de lascas u hojas con rastros complementarios ","Puntas_naturales_de_lascas_u_hojas_con_rastros_complementarios_"),
("Percutores de arista formatizada","Percutores_de_arista_formatizada"),
("Percutores s/nódulos no formatizados,con rastros complementarios","Percutores_s/nódulos_no_formatizados,con_rastros_complementarios"),
("Yunques: Nódulos con marcas de percusión concentradas en porción central de superficie natural.","Yunques_Nódulos_con_marcas_de_percusión_concentradas_en_porción_central_de_superficie_natural."),
("Litos rayados ","Litos_rayados_"),
("Rocas abrasivas con rastros complementarios (Abradidores)","Rocas_abrasivas_con_rastros_complementarios_Abradidores"),
("Núcleos de lascas: Poliédrico","Núcleos_de_lascas_Poliédrico"),
("Núcleos de lascas: Discoidal","Núcleos_de_lascas_Discoidal"),
("Núcleos de lascas: Bifacial","Núcleos_de_lascas_Bifacial"),
("Núcleos de lascas: Prismático atípico de lascas","Núcleos_de_lascas_Prismático_atípico_de_lascas"),
("Núcleos de lascas: Otros no diferenciados de lascas","Núcleos_de_lascas_Otros_no_diferenciados_de_lascas"),
("Núcleos de hojas: Prismático de hojas de extarcciones unidirecionales","Núcleos_de_hojas_Prismático_de_hojas_de_extarcciones_unidirecionales"),
("Núcleos de hojas: Prismático de hojas a extraccione bidireccionales","Núcleos_de_hojas_Prismático_de_hojas_a_extraccione_bidireccionales"),
("Núcleos de hojas: Piramidal","Núcleos_de_hojas_Piramidal"),
("Núcleos de hojas: Otros de hojas no diferenciados","Núcleos_de_hojas_Otros_de_hojas_no_diferenciados"),
("Núcleos a extracciones combinadas","Núcleos_a_extracciones_combinadas"),
("Nucleiformes","Nucleiformes"),
("Núcleos agotados","Núcleos_agotados"),
("Fragmentos no diferenciados de Núcleos","Fragmentos_no_diferenciados_de_Núcleos"),
("Desechos de talla enteros","Desechos_de_talla_enteros"),
("Desechos de talla fragmentados con talón","Desechos_de_talla_fragmentados_con_talón"),
("Desechos de talla fragmentados sin talón","Desechos_de_talla_fragmentados_sin_talón"),
("Desechos de talla no diferenciados: lascas adventicias,  fragmentos poliédricos o chunks u otros.","Desechos_de_talla_no_diferenciados_lascas_adventicias_fragmentos_poliédricos_o_chunks_u_otros.")
])

Roca = enum.Enum("Roca", [
    ('Roca no identificada', 'roca_no_identificada'),
    ("Arenisca", "arenisca"),
    ("Caliza silicificada", "caliza_silicificada"),
    ("Cuarcita de grano medio o grueso", "cuarcita_grano_medio_grueso"),
    ("Cuarzo cristalino", "cuarzo_cristalino"),
    ("Cuarzo lácteo", "cuarzo_lacteo"),
    ("Granito", "granito"),
    ("Ignimbrita", "ignimbrita"),
    ("Metacuarcita(grano fino)", "metacuarcita"),
    ("Metamórfica no identificada", "metaforica_no_id "),
    ("Obsidiana gris/negra, homogénea,manchada o bandeada", "obsidiana"),
    ("Sílices diversos(jaspes, calcedonias coloreadas)", "silices_diversos"),
    ("Vulcanitas ácidas, claras o coloreadas(riolitas, dacitas u otras) de grano fino", "vulcanitas_ac_claras"),
    ("Vulcanitas básicas grises o negras de grano fino", "vulcanitas_basicas"),
    ("Vulcanitas grano mediano a grueso", "vulcanitas_grano_mediano"),
    ("Xilópalos (vetas visibles)", "xilopalos"),
    ("Otros vidrios volcánicos claros o coloreados (no grises o negros)", "otros_vidrios")
    ])

Estado = enum.Enum("Estado", [
    ("Entera o completa", "entera"),
    ("Fracturada", "fracturada")
])

Tipo = enum.Enum("Tipo", [
    ("Simple", "simple"),
    ("Compuesta", "compuesta")
])

Eje = enum.Enum("Eje", [
    ("Eje técnico o de lascado", "eje_tecnico"),
    ("Eje morfológico", "eje_morfologico")
])

Clase_Art = enum.Enum("Clase Artefactual", [
    ("Artefactos con filos, puntas o superficies con rastros complementarios", "art_rastros"),
    ("Artefactos con filos, puntas y/o superficies formatizados", "art_sup"),
    ("Desechos de talla", "Desechos"),
    ("Nódulos con rastros complementarios", "nodulos_rastros"),
    ("Nódulos transportados sin rastros complementarios (rocas aloctonas)", "nodulos"),
    ("Núcleos", "nucleos")
])

Cant_Filos = enum.Enum("Cantidad de filos", [
    "0","1","2","3","4","5","6","7","8","9","20"
])

Cant_Puntas = enum.Enum("Cantidad de puntas formatizadas", [
    "0","1","2","3","4","5","6","7","8","9","20"
])

Clasificacion_Forma_Base = enum.Enum("Clasificación de forma base", [
    ("Forma Base no diferenciada (0Z)", "0z"),
    ("Hoja de aristas dobles o múltiples (3B)", "3b"),
    ("Hoja no diferenciada (3Z)", "3z"),
    ("Hoja reciclada (4C)", "4c"),
    ("Laja o nódulo tabular no rodado (1G)", "1g"),
    ("Lasca angular (2D)", "2d"),
    ("Lasca con dorso natural (2C)", "2c"),
    ("Lasca de arista simple o doble (2E)", "2e"),
    ("Lasca de flanco de nucleo (2H)", "2h"),
    ("Lasca de tableta de núcleo (2I)", "2i"),
    ("Lasca en cresta (2G)", "2g"),
    ("Lasca no diferenciada (2Z)", "2z"),
    ("Lasca plana (2F)", "2f"),
    ("Lasca primaria (2A)", "2a"),
    ("Lasca reciclada (4B)", "4b"),
    ("Lasca secundaria (2B)", "2b"),
    ("Lasca semi-tableta de núcleo (2J)", "2j"),
    ("Módulo no diferenciado (1Z)", "1z"),
    ("Nódulo o rodado a facetas naturales (1E)", "1e"),
    ("Nódulo tabular (rodado) (1F)", "1f"),
    ("Artefacto formatizado reciclado (4A)", "4a"),
    ("Artefacto reciclado, no diferenciado (4Z)", "4z"),
    ("Bloque no transportable, con/sin facetas (1H)", "1h"),
    ("Clasto (frag.anguloso natural) (1I)", "1i"),
    ("Concreción nodular(con restos de matriz) (1J)", "1j"),
    ("Núcleo reciclado 4D", "4d")
])

Cant_Cicatrices = enum.Enum("Cantidad de cicatrices de lascado", [
    "0","1","2","3","4","5","6","7","8","9","20"
])

Origen_extraccion = enum.Enum("Origen de la extracción", [
    ("Origen no diferenciado (9)", "9"),
    ("Adelgazamiento o reducción bifacial (2)", "2"),
    ("Reactivación de núcleos (4)", "4"),
    ("Reactivación de útiles o instrumento (3)", "3"),
    ("Talla de extracción (1)", "1")
])

Alteraciones = enum.Enum("Alteraciones", [
    ("Alteraciones no diferenciadas (Z0)", "az0"),
    ("Alteraciones térmicas múltiples (E4)", "ae4"),
    ("Alteraciones térmicas no diferenciadas (E0)", "ae0"),
    ("Alteracion térmica del color (E3)", "ae3"),
    ("Craqueleado (E2)", "ae2"),
    ("Desprendimientos cupulares u 'hoyuelos' (E1)", "ae1"),
    ("Lustre sin gradaciones diferenciadas (A0)", "aa0"),
    ("Patina grisacea o blanquecina 'en costra' (B2)", "ab2"),
    ("Patina rojiza o 'barniz del desierto' (B1)", "ab1"),
    ("Patina sin gradaciones diferenciadas (B0)", "ab0"),
    ("Rodamiento sin gradaciones (D0)", "ad0"),
    ("Ventifaccion sin gradaciones (C0)", "ac0")
])

Estado_Talon = enum.Enum("Estado del talón", [
    ("Entero", "entero"),
    ("Fracturado", "fracturado"),
    ("Rebajado", "rebajado"),
    ("Eli", "eli")
])

Superficie_Talon = enum.Enum("Superficie talón o plataforma", [
    ("Cortical (Ct)", "ct"),
    ("Liso-Cortical  (LiC)", "lic"),
    ("Liso (Li)", "li"),
    ("Facetado (Fc)", "fc"),
    ("Filiforme (Fi)", "fi"),
    ("Puntiforme (Pt)", "pt")
])

Clase_tecnica = enum.Enum("Clase técnica", [
    ("Artefacto con adelgazamiento bifacial", "acab"),
    ("Con reducción bifacial", "crb"),
    ("Bifacial marginales", "cm"),
    ("Adelgazamiento unifacial", "au"),
    ("Reducción unifacial", "ru"),
    ("Unifacial marginales", "um"),
    ("Talla de extracción sin formatización", "tesf"),
    ("Lito transportado (alóctono) no tallado", "ltnt")
])

Reduc_uni_sbordes = enum.Enum("Reducción unifacial sin bordes", ["Si", "No"])

Las_inv_lim = enum.Enum("Lascado inverso limitante", ["Si", "No"])

Forma_geo = enum.Enum("Forma geométrica", [
    #-----Filos-----
    ("Filo - Convexo atenuado o muy atenuado (A1)", "FA1"),
    ("Filo - Convexo medio (A2)", "FA2"),
    ("Filo - Convexo semicircular (A3)", "FA3"),
    ("Filo - Cóncavo atenuado o muy atenuado (B1)", "FB1"),
    ("Filo - Cóncavo medio (B2)", "FB2"),
    ("Filo - Cóncavo semicircular (B3)", "FB3"),
    ("Filo - Recto (C)", "FC"),
    ("Filo - Irregular - Combinados B/c ó A/C (D)", "FD"),
    #-----Puntas manuales (sección)-----
    ("Punta manual - Triédrica (E)", "PE"),
    ("Punta manual - Cuadrangular o trapezoidal (F)", "PF"),
    ("Punta manual - Plano-convexa (G)", "PG"),
    ("Punta manual -  Biconvexa (H)", "PH"),
    ("Punta manual - No diferenciada (Z)", "PZ"),
    #-----Limbos-----
    ("Limbo - Triangular corto convexilíneo (I)", "LI"),
    ("Limbo - Triangular largo convexilíneo (J)", "LJ"),
    ("Limbo - Triangular corto rectililneo (K)", "LK"),
    ("Limbo - Traingular largo rectilíneo (L)", "LL"),
    ("Limbo -Triangular corto concavilíneo (M)", "LM"),
    ("Limbo - Triangular largo concavilíneo (N)", "LN"),
    ("Limbo -Lanceolado (n)", "Ln"),
    ("Limbo -Lanceolado con bordes medios paralelos (O)", "LO"),
    ("Limbo - En mandorla (bipunta lanceolada) (P)", "LP"),
    ("Limbo - Lanceolada asimétrica o almendrada. (Q)", "LQ"),
    #-----Bordes de pedúnculos-----
    ("Borde - Paralelos o subparalelos (R)", "BR"),
    ("Borde - Divergentes hacia la base- (R)", "BD"),
    ("Borde - Convergentes, idem.- (S)", "BC"),
    ("Borde - Expandidos. (T)", "BT"),
    #-----Contornos-----
    ("Contorno - Oval (U)", "CU"),
    ("Contorno - Elípticos (V)", "CV"),
    ("Contorno - lanceolado (O)", "CO"),
    ("Contorno - Almendrado (Q)", "CQ"),
    ("Contorno - No diferenciada. (Z)", "CZ"),
    #-----Delineación aristas de piezas bifaciales-----
    ("Delineacion - Regular normal (X1)", "DX1"),
    ("Delineacion - Sinuosa regula (X2)", "DX2"),
    ("Delineacion - Sinuosa irregular (X3)", "DX3"),
    ("Delineacion - No diferenciada (Z)", "DZ")
])

Estado_bisel = enum.Enum("Estado de bisel", [
    ("No diferenciado (Z0)", "ezo"),
    ("Activo no astillado (A1)", "ea1"),
    ("Activo Astiladol (A2)", "ea2"),
    ("Embotado(+80°) (B1)", "eb1"),
    ("Embotado astillado (B2)", "eb2"),
    ("Con astillad.escalonadas (B3)", "eb3"),
    ("Recto (C)", "ec")
])

Mantenimiento = enum.Enum("Mantenimiento", ["Si", "No"])

Parte_pasiva = enum.Enum("Parte pasiva", [
    ("No diferenciado", "ppnd"),
    ("Dorso formatizado", "ppdf"),
    ("Dorso abatido (por lascado único)", "ppda"),
    ("Formatización sumaria de acomodación", "ppfsa"),
    ("Corteza reservada", "ppcr"),
    ("Plano de fractura utilizado", "ppcf"),
    ("Filo en ficha", "ppff"),
])

Forma_lascados = enum.Enum("Forma de lascados", [
    ("No diferenciado", "flnd"),
    ("Lasca simple", "flls"),
    ('Simple laminar "en golpe de buril"', "flgb"),
    ("Paralelo corto", "flpc"),
    ("Paralelo laminar", "flpl"),
    ("Escamoso", "fle"),
    ("Escamoso escalonado", "flee")
])

Sustancia = enum.Enum("Sustancia adherida", ["Si", "No"])

# Create db models and views

class Observacion(db.Model):
    __tablename__ = 'Observacion'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column('Nombre o etiqueta de la observación', db.String(64))
    sitio = db.Column('Sitio o Localidad', db.String(64))
    latitud = db.Column('Latitud', db.Float())
    longitud = db.Column('Longitud', db.Float())
    sigla = db.Column('Sigla del sitio', db.String(64))
    capa = db.Column('Capa o nivel', db.String(64))
    coleccion = db.Column('Colección o ano', db.String(64))
    operador = db.Column('Operador', db.String(64))

    user_id = db.Column(db.Integer(), db.ForeignKey(User.id))
    user = db.relationship(User, backref='observaciones')

    fecha = db.Column('Fecha', db.DateTime)
    hoja = db.Column('Hoja N°', db.Integer)



    def __str__(self):
        return self.nombre

class Artefacto(db.Model):
    __tablename__ = 'artefacto'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column('Nombre o etiqueta del artefacto', db.String(64),
                        nullable=False)
    numero = db.Column('Número o sigla de la pieza', db.Integer)
    cuadro = db.Column('Cuadro o microsector', db.String(64))
    roca = db.Column('Roca o materia prima', db.Enum(Roca))
    estado = db.Column(db.Enum(Estado))
    tipo = db.Column(db.Enum(Tipo))
    eje = db.Column(db.Enum(Eje))
    clase_art = db.Column(db.Enum(Clase_Art))
    cant_filos = db.Column(db.Enum(Cant_Filos))
    cant_puntas = db.Column(db.Enum(Cant_Puntas))
    clasificacion_Forma_Base = db.Column(db.Enum(Clasificacion_Forma_Base))
    cant_Cicatrices = db.Column(db.Enum(Cant_Cicatrices))
    origen = db.Column(db.Enum(Origen_extraccion))
    alteraciones = db.Column(db.Enum(Alteraciones))
    estado_talon = db.Column(db.Enum(Estado_Talon))
    sup_talon = db.Column(db.Enum(Superficie_Talon))
    ancho_talon = db.Column(db.Integer)
    ancho_pieza = db.Column(db.Integer, nullable=False)
    long_pieza = db.Column(db.Integer, nullable=False)
    espesor_pieza = db.Column(db.Integer, nullable=False)
    peso_pieza = db.Column(db.Integer)
    clase_tecnica = db.Column(db.Enum(Clase_tecnica))
    reduc_uni_sbordes = db.Column(db.Enum(Reduc_uni_sbordes))
    las_inv_lim = db.Column(db.Enum(Las_inv_lim))

    procedimientos = db.relationship('Procedimiento', backref='artefacto')

    forma_geo = db.Column(db.Enum(Forma_geo))
    angulo_bisel = db.Column(db.Integer)
    estado_bisel = db.Column(db.Enum(Estado_bisel))
    mantenimiento = db.Column(db.Enum(Mantenimiento))

    #detalles = db.relationship('Detalle', backref='artefacto')

    parte_pasiva =  db.Column(db.Enum(Parte_pasiva))
    forma_lascados = db.Column(db.Enum(Forma_lascados))
    sustancia = db.Column(db.Enum(Sustancia))
    ubicacion_sustancia = db.Column('Ubicacion de la sustancia', db.String(64))
    obs = db.Column('Observaciones', db.String(200))

    observacion_id = db.Column(db.Integer(), db.ForeignKey(Observacion.id))
    observacion = db.relationship(Observacion, backref='artefactos')

    @hybrid_property
    def tamano(self):
        try:
            mayor = db.session.query(
                db.func.max(self.long_pieza, self.ancho_pieza)
            ).first()[0]
            return clasificacion_tamano(mayor)
        except:
            return 'Datos faltantes'

    @hybrid_property
    def mod_ancho_largo_pieza(self):
        try:
            pendiente = db.session.query(
                cast(self.long_pieza / self.ancho_pieza, Float)
            ).scalar()
            return modulo_largo_ancho(pendiente)
        except:
            return 'Datos faltantes'

    @hybrid_property
    def mod_ancho_espesor_pieza(self):
        try:
            a_e = db.session.query(
                cast(self.ancho_pieza / self.espesor_pieza, Float)
            ).scalar()
            return modulo_ancho_espesor(a_e)
        except:
            return 'Datos faltantes'

    def __str__(self):
        return self.nombre

class Procedimiento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50))
    artefacto_id = db.Column(db.Integer, db.ForeignKey('artefacto.id'))

    def __str__(self):
        return self.nombre

class FotosArtefactos(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(64))
    path = db.Column(db.Unicode(128))
    artefacto_id = db.Column(db.Integer(), db.ForeignKey(Artefacto.id))
    artefacto = db.relationship(Artefacto, backref='fotos')

    def __unicode__(self):
        return self.name

class Detalle(db.Model):
    __tablename__ = 'Detalle'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column('Nombre o etiqueta del detalle',
                        db.String(64), nullable=False)
    ancho_talon = db.Column(db.Integer)
    ancho_pieza = db.Column(db.Integer, nullable=False)
    long_pieza = db.Column(db.Integer)
    espesor_pieza = db.Column(db.Integer, nullable=False)
    clase_tecnica = db.Column(db.Enum(Clase_tecnica))
    reduc_uni_sbordes = db.Column(db.Enum(Reduc_uni_sbordes))
    las_inv_lim = db.Column(db.Enum(Las_inv_lim))

    procedimientos = db.relationship('Procedimiento2', backref='detalle')

    forma_geo = db.Column(db.Enum(Forma_geo))
    angulo_bisel = db.Column(db.Integer)
    estado_bisel = db.Column(db.Enum(Estado_bisel))
    mantenimiento = db.Column(db.Enum(Mantenimiento))
    subgrupos = db.Column(db.Enum(Subgrupos))
    parte_pasiva =  db.Column(db.Enum(Parte_pasiva))
    ubicacion_pasiva = db.Column('Ubicacion parte pasiva', db.String(64))

    artefacto_id = db.Column(db.Integer(), db.ForeignKey(Artefacto.id))
    artefacto = db.relationship(Artefacto, backref='detalles')


    @hybrid_property
    def mod_ancho_espesor_pieza(self):
        try:
            a_e = db.session.query(
                cast(self.ancho_pieza / self.espesor_pieza, Float)
            ).scalar()
            return modulo_ancho_espesor(a_e)
        except:
            return 'Datos faltantes'

    def __str__(self):
        return self.nombre

class Procedimiento2(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50))
    detalle_id = db.Column(db.Integer, db.ForeignKey('Detalle.id'))

    def __str__(self):
        return self.nombre

class Desecho(db.Model):
    __tablename__ = 'Desecho'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column('Nombre o etiqueta del desecho', db.String(64))
    sitio = db.Column('Sitio o Localidad', db.String(64))
    sigla = db.Column('Sigla del sitio', db.String(64))
    capa = db.Column('Capa o nivel', db.String(64))
    cuadro = db.Column('Cuadro o microsector', db.String(64))
    coleccion = db.Column('Colección o ano', db.String(64))
    nro_sintalon = db.Column('Piezas fracturadas sin talon',
                            db.Enum(Cant_Filos))
    nro_contalon = db.Column('Piezas fracturadas con talon',
                            db.Enum(Cant_Filos))
    lote = db.Column('Lote', db.Integer)
    estado = db.Column(db.Enum(Estado))
    ancho_talon = db.Column(db.Integer)
    ancho_pieza = db.Column(db.Integer)
    long_pieza = db.Column(db.Integer)
    espesor_pieza = db.Column(db.Integer)
    sup_talon = db.Column(db.Enum(Superficie_Talon))

    observacion_id = db.Column(db.Integer(), db.ForeignKey(Observacion.id))
    observacion = db.relationship(Observacion, backref='desechos')

    def __str__(self):
        return self.nombre

class FotosDesechos(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(64))
    path = db.Column(db.Unicode(128))

    desecho_id = db.Column(db.Integer(), db.ForeignKey(Desecho.id))
    desecho = db.relationship(Desecho, backref='fotos')

    def __unicode__(self):
        return self.name

class ObservacionAdmin(sqla.ModelView):
    column_labels = dict(id = 'Id',
                         nombre = 'Nombre o etiqueta de la observación',
    sitio = 'Sitio o Localidad',
    latitud = 'Latitud',
    longitud = 'Longitud',
    sigla = 'Sigla del Sitio',
    capa = 'Capa o nivel',
    coleccion = 'Colección',
    operador = 'Operador',
    user = 'Usuario',
    fecha = 'Fecha',
    hoja = 'Hoja N°')

    column_list = ('nombre',
                   'sitio',
                   'sigla',
                   'capa',
                   'coleccion',
                   'operador',
                   'user',
                   'fecha',
                   'hoja')

    column_sortable_list = column_list

    column_filters = column_list

    form_columns = column_list

    can_export = True

    def is_accessible(self):
        return login.current_user.is_authenticated

class ArtefactoAdmin(sqla.ModelView):
    """ Flask-admin can not automatically find a association_proxy yet.
    You will need to manually define the column
    in list_view/filters/sorting/etc. Moreover,
    support for association proxies to association proxies
    (e.g.: Detalle_values) is currently limited to column_list only."""

    column_labels = dict(numero = 'N°',
                         nombre = 'Nombre o etiqueta del artefacto',
                         observacion = 'Observación a la que pertenece',
                         cuadro = 'Cuadro o microsector',
                         roca = 'Roca o materia prima',
                         estado = 'Estado',
                         tipo = "Tipo",
                         eje = "Eje",
                         clase_art = 'Clase Artefactual',
                         cant_filos = 'N° de filos/ cicatrices',
                         cant_puntas = 'N° de puntas formatizadas',
                         clasificacion_Forma_Base = 'Tipo de forma base',
                         cant_Cicatrices = 'N° cicatrices lascado',
                         origen = 'Origen',
                         estado_talon = 'Estado del talón',
                         sup_talon = 'Sup talón o plataforma',
                         ancho_talon = 'Ancho talón (mm)',
                         ancho_pieza = 'Ancho pieza (mm)',
                         tamano = 'Tamano de la pieza',
                         long_pieza = 'Longitud pieza (mm)',
                         espesor_pieza = 'Espesor pieza (mm)',
                         peso_pieza = 'Peso pieza (g)',
                         mod_ancho_largo_pieza = 'Módulo ancho-largo',
                         mod_ancho_espesor_pieza = 'Módulo ancho-espesor',
                         clase_tecnica = 'Clase técnica',
                         reduc_uni_sbordes = "Reduccion unifacial sin bordes",
                         las_inv_lim = "Lascado inverso limitante",
                         procedimientos = "Procedimiento técnico de formatización",
                         forma_geo = "Forma geométrica",
                         angulo_bisel = "Ángulo bisel estimado",
                         estado_bisel = "Estado bisel",
                         mantenimiento = "Mantenimiento",
                         #detalle = "Grupos y Subgrupos",
                         parte_pasiva = "Parte pasiva",
                         forma_lascados = "Forma de los lascados de formatización",
                         sustancia = "Sustancia adherida",
                         ubicacion_sustancia = "Ubicacion de la sustancia adherida",
                         obs = "Observaciones")

    column_list = ['numero',
                   'nombre',
                   'observacion',
                   'cuadro',
                   'roca',
                   'estado',
                   'tipo',
                   'eje',
                   'clase_art',
                   'cant_filos',
                   'cant_puntas',
                   'clasificacion_Forma_Base',
                   'cant_Cicatrices', 'origen',
                   'alteraciones', 'estado_talon',
                   'sup_talon',
                   'ancho_talon',
                   'long_pieza',
                   'ancho_pieza',
                   'tamano',
                   'espesor_pieza',
                   'peso_pieza',
                   'mod_ancho_largo_pieza',
                   'mod_ancho_espesor_pieza',
                   'clase_tecnica',
                   'reduc_uni_sbordes',
                   'las_inv_lim',
                   'procedimientos',
                   'forma_geo',
                   'angulo_bisel',
                   'estado_bisel',
                   'mantenimiento',
                   #'detalle',
                   'parte_pasiva',
                   'forma_lascados',
                   'sustancia',
                   'ubicacion_sustancia',
                   'obs']

    lista_sin_hibridos = [col for col in column_list if col != 'tamano']
    lista_sin_hibridos = [col for col in lista_sin_hibridos
                                    if col != 'mod_ancho_largo_pieza']
    lista_sin_hibridos = [col for col in lista_sin_hibridos
                                    if col != 'mod_ancho_espesor_pieza']

    column_sortable_list = lista_sin_hibridos

    column_filters = lista_sin_hibridos

    form_columns = lista_sin_hibridos

    can_export = True

    def is_accessible(self):
        return login.current_user.is_authenticated


class ProcedimientoAdmin(sqla.ModelView):
    column_labels = dict(
    id = 'Id',
    nombre = 'Nombre',
    artefacto_id = 'Artefacto',
    )

    column_list = ['id', 'nombre']

class FotosArtefactosView(sqla.ModelView):
    def _list_thumbnail(view, context, model, name):
        if not model.path:
            return ''

        return Markup('<img src="%s">' % url_for('static',
        filename=formadmin.thumbgen_filename(model.path)))

    column_formatters = {
        'path': _list_thumbnail
    }

    # Alternative way to contribute field is to override it completely.
    # In this case, Flask-Admin won't attempt to merge various parameters for the field.
    form_extra_fields = {
        'path': formadmin.ImageUploadField('Image',
                                      base_path=file_path,
                                      thumbnail_size=(100, 100, True))
    }

    def is_accessible(self):
        return login.current_user.is_authenticated


class DetalleAdmin(sqla.ModelView):

    column_labels = dict(nombre = 'Nombre o etiqueta del detalle',
                         artefacto = 'Artefacto al que pertenece',
                         ancho_talon = 'Ancho del talón',
                         long_pieza = 'Longitud pieza (mm)',
                         ancho_pieza = 'Ancho pieza (mm)',
                         espesor_pieza = 'Espesor pieza (mm)',
                         mod_ancho_espesor_pieza = 'Módulo ancho-espesor',
                         clase_tecnica = 'Clase técnica',
                         reduc_uni_sbordes = "Reduccion unifacial sin bordes",
                         las_inv_lim = "Lascado inverso limitante",
                         procedimientos = "Procedimiento técnico de formatización",
                         forma_geo = "Forma geométrica",
                         angulo_bisel = "Ángulo bisel estimado",
                         estado_bisel = "Estado bisel",
                         mantenimiento = "Mantenimiento",
                         subgrupos = "Grupos y subgrupos",
                         parte_pasiva = "Parte pasiva",
                         ubicacion_pasiva = "Ubicación parte pasiva")

    column_list = ('nombre',
                   'artefacto',
                   'ancho_talon',
                   'long_pieza',
                   'ancho_pieza',
                   'espesor_pieza',
                   'mod_ancho_espesor_pieza',
                   'clase_tecnica',
                   'reduc_uni_sbordes',
                   'las_inv_lim',
                   'procedimientos',
                   'forma_geo',
                   'angulo_bisel',
                   'estado_bisel',
                   'mantenimiento',
                   'subgrupos',
                   'parte_pasiva',
                   'ubicacion_pasiva')

    lista_sin_hibridos = [col for col in column_list if col != 'mod_ancho_espesor_pieza']

    column_sortable_list = lista_sin_hibridos

    column_filters = lista_sin_hibridos

    form_columns = lista_sin_hibridos

    can_export = True


    def is_accessible(self):
        return login.current_user.is_authenticated

class Procedimiento2Admin(sqla.ModelView):
    column_labels = dict(
    id = 'Id',
    nombre = 'Nombre',
    detalle_id = 'Detalle'
    )

    column_list = ['id', 'nombre']

class DesechoAdmin(sqla.ModelView):
    column_labels = dict(nombre = 'Nombre o etiqueta del desecho',
                         sitio = 'Sitio o Localidad',
                         sigla = 'Sigla del Sitio',
                         capa = 'Capa o nivel',
                         cuadro = 'Cuadro o microsector',
                         coleccion = 'Colección',
                         nro_sintalon = 'N° Piezas fracturadas sin talon',
                         nro_contalon = 'N° Piezas fracturadas con talon',
                         lote = 'Lote',
                         estado = "Estado",
                         ancho_talon = "Ancho del talón",
                         ancho_pieza = "Ancho de la pieza",
                         long_pieza = "Longitud de la pieza",
                         espesor_pieza = "Espesor de la pieza",
                         sup_talon = "Superficie talon")

    column_list = ('nombre',
                   'sitio',
                   'sigla',
                   'capa',
                   'cuadro',
                   'coleccion',
                   'nro_sintalon',
                   'nro_contalon',
                   'lote',
                   'estado',
                   'ancho_talon',
                   'ancho_pieza',
                   'long_pieza',
                   'espesor_pieza',
                   'sup_talon')

    column_sortable_list = column_list

    column_filters = column_list

    form_columns = column_list

    can_export = True


    def is_accessible(self):
        return login.current_user.is_authenticated

class FotosDesechosView(sqla.ModelView):
    def _list_thumbnail(view, context, model, name):
        if not model.path:
            return ''

        return Markup('<img src="%s">' % url_for('static',
        filename=formadmin.thumbgen_filename(model.path)))

    column_formatters = {
        'path': _list_thumbnail
    }

    # Alternative way to contribute field is to override it completely.
    # In this case, Flask-Admin won't attempt to merge various parameters for the field.
    form_extra_fields = {
        'path': formadmin.ImageUploadField('Image',
                                      base_path=file_path,
                                      thumbnail_size=(100, 100, True))
    }

    def is_accessible(self):
        return login.current_user.is_authenticated

# Create customized model view class
class MyModelView(sqla.ModelView):

    def is_accessible(self):
        return login.current_user.is_authenticated

# Create customized index view class that handles login & registration
class MyAdminIndexView(admin.AdminIndexView):

    @expose('/')
    def index(self):
        if not login.current_user.is_authenticated:
            return redirect(url_for('.login_view'))
        return super(MyAdminIndexView, self).index()

    @expose('/login/', methods=('GET', 'POST'))
    def login_view(self):
        # handle user login
        form = LoginForm(request.form)
        if helpers.validate_form_on_submit(form):
            user = form.get_user()
            login.login_user(user)

        if login.current_user.is_authenticated:
            return redirect(url_for('.index'))
        link = '<p>Don\'t have an account? <a href="' + url_for('.register_view') + '">Click here to register.</a></p>'
        self._template_args['form'] = form
        self._template_args['link'] = link
        return super(MyAdminIndexView, self).index()

    @expose('/register/', methods=('GET', 'POST'))
    def register_view(self):
        form = RegistrationForm(request.form)
        if helpers.validate_form_on_submit(form):
            user = User()

            form.populate_obj(user)
            # we hash the users password to avoid saving it as plaintext in the db,
            # remove to use plain text:
            user.password = generate_password_hash(form.password.data)

            db.session.add(user)
            db.session.commit()

            login.login_user(user)
            return redirect(url_for('.index'))
        link = '<p>Already have an account? <a href="' + url_for('.login_view') + '">Click here to log in.</a></p>'
        self._template_args['form'] = form
        self._template_args['link'] = link
        return super(MyAdminIndexView, self).index()

    @expose('/logout/')
    def logout_view(self):
        login.logout_user()
        return redirect(url_for('.index'))


# Create admin
admin = admin.Admin(app, 'ARQcheros', index_view=MyAdminIndexView(), base_template='my_master.html')

# Add view
#admin.add_view(MyModelView(User, db.session))
admin.add_view(ObservacionAdmin(Observacion, db.session))
admin.add_view(ArtefactoAdmin(Artefacto, db.session))
admin.add_view(ProcedimientoAdmin(Procedimiento, db.session))
admin.add_view(Procedimiento2Admin(Procedimiento2, db.session))
admin.add_view(FotosArtefactosView(FotosArtefactos, db.session))
admin.add_view(DetalleAdmin(Detalle, db.session))
admin.add_view(DesechoAdmin(Desecho, db.session))
admin.add_view(FotosDesechosView(FotosDesechos, db.session))



if __name__ == '__main__':

    # Build a sample db on the fly, if one does not exist yet.
    app_dir = os.path.realpath(os.path.dirname(__file__))
    database_path = os.path.join(app_dir, app.config['DATABASE_FILE'])
    if not os.path.exists(database_path):
        build_sample_db()

     # Create db
    db.create_all()

    # Run app
    app.run(debug=True)
