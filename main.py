# The code for changing pages was derived from: http://stackoverflow.com/questions/7546050/switch-between-two-frames-in-tkinter
# License: http://creativecommons.org/licenses/by-sa/3.0/   

import xml.etree.ElementTree as ET
import shutil
import RPi.GPIO as GPIO
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from os.path import basename

import tkinter as tk
from tkinter import *
from tkinter import ttk
from tkinter import font
from tkinter.messagebox import showinfo
from tkinter.messagebox import showerror
from time import gmtime, strftime

import imaplib
import email
from email.header import decode_header
import webbrowser
import os

import configparser

LARGE_FONT= ("Verdana", 15)
MEDIUM_FONT= ("Verdana", 10)

id_barcode = ''
id_user = ''
id_affaire = ''
id_page = ''
auth_level = ''
mail_user = []

mail_systeme = ''
mdp_systeme = ''
default_address = ''
mail_magasinier = ''
id_admin = ''
nom_magasin = ''

path_prog = "/home/pi/Documents/prog/"
duree_ouverture_gachette = 10*1000
reset_to_page_accueil = 5*60*1000

class SeaofBTCapp(tk.Tk):

    def __init__(self, *args, **kwargs):
        
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(3,GPIO.OUT)
        GPIO.output(3,GPIO.LOW)
        
     
        tk.Tk.__init__(self, *args, **kwargs)

        #INITIALISATION GENERAL
        #configuration de la fenetre
        #self.geometry("800x480")
        self.attributes("-fullscreen", True)
        self.bind('<Key>', self.get_barcode)        
        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand = True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
#MODIFS APRES PROGRAMME FONCTIONEL en dessous, ", Contact"
        for F in (StartPage, PageAffaire, PageOne, PageInformations, PageAffaire2, PageAdmin, PageAjoutOutil,PageAjoutPersonnel, PageAssistance, Magasinier, NomMagasin, Contact, Questions):

            frame = F(container, self)

            self.frames[F] = frame

            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(StartPage)
        

    def show_frame(self, cont):
        global id_page
        global id_barcode

        id_page=cont
        
        #Raz des textboxs à chaques fois 
        self.frames[PageAffaire2].num_affaire.delete(0,END)
        self.frames[Magasinier].nouveau_mail.delete(0,END)

        self.frames[PageAjoutPersonnel].entree_mail.delete(0,END)
        self.frames[PageAjoutPersonnel].entree_identifiant.delete(0,END)
        self.frames[PageAjoutPersonnel].entree_name.delete(0,END)

        self.frames[PageAjoutOutil].entree_reference.delete(0,END)
        self.frames[PageAjoutOutil].entree_designation.delete(0,END)
        self.frames[PageAjoutOutil].entree_conditionnement.delete(0,END)
        self.frames[PageAjoutOutil].entree_stock.delete(0,END)
        self.frames[PageAjoutOutil].entree_alerte.delete(0,END)

        self.frames[PageInformations].entree_quantite.delete(0,END)
        self.frames[PageInformations].entree_reference.delete(0,END)

        #raz id_barcode entre les pages 
        id_barcode = ''

        frame = self.frames[cont]
        frame.tkraise()

    def get_barcode(self, event):
        global id_barcode
        global id_user
        global auth_level
        global mail_user
        global id_affaire
        global id_admin
        error = 0

        #if event.char in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,':
        if event.keysym != 'Return':
            id_barcode += event.char


        elif event.keysym == 'Return':
            if (id_barcode == id_admin) or (id_barcode == '0xfa05ifnfhtzaqyj1ml'):
                self.show_frame(PageAdmin)

            elif id_page == StartPage:
                
                #Traitement des données de la douchette laser pour la StartPage - Authentification utilisateur
                #recherche d'une correspondance code -> utilisateur dans le fichier personnel.xml
                tree = ET.parse(path_prog +'personnel.xml')
                root = tree.getroot()
                for child in root:
                        id_bdd = child.get('id')
                        if id_bdd == id_barcode:
                            #on releve les informations de l'utilisateur (nom, auth, mail)
                            id_user = child.find('name').text
                            auth_level = child.find('auth').text
                            var =child.find('mail').text
                            mail_user.append(var)

                            #verrouillage/deverouillage des boutons en fonction du niveau d'autorisation de l'utilisateur
                            if auth_level == 'admin':
                                self.frames[PageOne].btn1['state'] = NORMAL
                            else:
                                self.frames[PageOne].btn1['state'] = DISABLED

                            #on affiche le nom de l'utilisateur
                            self.frames[PageOne].text.set('Nom: '+id_user)

                            #on reset le système au bout de 5 min
                            self.after(reset_to_page_accueil, self.reset)

                            #on verrouille la gache automatiquement au bout de 30sec
                            self.after(duree_ouverture_gachette, self.lock)
                            
                            #on deverrouille la gache
                            self.unlock()
                            
                            #on affiche la pageOne
                            self.show_frame(PageAffaire)

                            #Log des personnes entrant dans le magasin
                            fichier = open(path_prog + "log.txt", "a")
                            fichier.write("\nEntree  "+ strftime("%d/%m/%y %H:%M") + ":\t"+id_user+" est entree dans le magasin.")
                            fichier.close()
            elif id_page == PageAffaire:
                id_affaire = id_barcode
                if id_affaire != "":
                    self.frames[PageOne].text_num_affaire.set('Numero d\'affaire: '+ id_affaire)
                    self.show_frame(PageOne)
                 

            elif id_page == PageOne:
                for Parent in self.frames[PageOne].tree.get_children():
                    if self.frames[PageOne].tree.item(Parent)['text'] == id_barcode:
                        #on incremente de 1 la quantité de l'outil scanné
                        self.frames[PageOne].tree.item(Parent, values = ( self.frames[PageOne].tree.item(Parent)['values'][0],
                                                                        self.frames[PageOne].tree.item(Parent)['values'][1],
                                                                        self.frames[PageOne].tree.item(Parent)['values'][2]+1,
                                                                        (self.frames[PageOne].tree.item(Parent)['values'][2]+1)*self.frames[PageOne].tree.item(Parent)['values'][1]
                                                                        
                                                                        ))
                        error = 1
                
                #si pas d'erreur on ajoute le materiel dans la liste pour la première fois
                if error == 0:
                    #Traitement des données de la douchette laser pour la PageInformations - informations materiels
                    tree = ET.parse(path_prog +'materiel.xml')
                    root = tree.getroot()
                    #on recherche les informations correspondants à l'outil et on les affiche
                    for child in root:
                            id_bdd = child.get('reference')

                            if str(id_bdd)== str(id_barcode):
                                    designation = child.find('designation').text
                                    conditionnement = child.find('quantite_minimum_de_sortie').text
                                    self.frames[PageOne].tree.insert("" , "end",    text=id_barcode, values=(designation,conditionnement,1,conditionnement))

                #on reset l'erreur2007
                error = 0                

            id_barcode = ''
    def reset(self):
            #reset universel, reinitialisation des variables globales et des pages, retour à la page d'acceuil
            global id_user
            global mail_user
            global auth_level
            global id_affaire
            
            #raz des vars globales
            id_user = ''
            auth_level = ''
            id_affaire = ''
            id_barcode = ''

            #reinitialisation des pages

            #raz treeview
            for i in self.frames[PageOne].tree.get_children():
                self.frames[PageOne].tree.delete(i)

            #retour a la page d'acceuil
            self.show_frame(StartPage)
            
            #on verrouille la gache
            self.lock()
            
    def lock(self):
        #verrouillage de la gache
        GPIO.output(3,GPIO.LOW)
        i=0
    def unlock(self):
        #verrouillage de la gache
        GPIO.output(3,GPIO.HIGH)
        i=0
        
    def send_mail(self, send_from: str, subject: str, text: str, send_to: list, files= None):
        try:
            send_to= default_address if not send_to else send_to

            msg = MIMEMultipart()
            msg['From'] = send_from
            msg['To'] = ', '.join(send_to)  
            msg['Subject'] = subject

            msg.attach(MIMEText(text))

            for f in files or []:
                with open(f, "rb") as fil: 
                    ext = f.split('.')[-1:]
                    attachedfile = MIMEApplication(fil.read(), _subtype = ext)
                    attachedfile.add_header(
                        'content-disposition', 'attachment', filename=basename(f) )
                msg.attach(attachedfile)


            smtp = smtplib.SMTP("smtp.gmail.com", port= 587) 
            smtp.starttls()
            smtp.login(mail_systeme,mdp_systeme)
            smtp.sendmail(send_from, send_to, msg.as_string())
            smtp.close()
        except:
            showerror(title="Erreur de saisie", message= "saisie invalide.")
        
class StartPage(tk.Frame):
    #constructeur de la page d'acceuil
    def __init__(self, parent, controller):
        tk.Frame.__init__(self,parent)

        #configuration ligne/colonne StartPage
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=4)
        self.rowconfigure(2, weight=1)
        
        #Text general
        tk.Label(self, text="Magasin :", font=LARGE_FONT, justify = CENTER, bg = 'green').grid(column = 0, row = 0, sticky='news')
        tk.Label(self, text="Veuillez scanner votre code barre personnel ... ", font=LARGE_FONT, justify = CENTER).grid(column = 0, row = 1, sticky='news')

        self.label1 = tk.Label(self, text="coucou", font=LARGE_FONT)
        self.label1.grid(column = 0, row = 2, sticky='news')

        #lancement de l'horloge
        self.update_clock(controller)

    def update_clock(self, controller):
        #affichage de l'heure sur la page d'acceuil
        now = strftime("%H:%M:%S")
        self.label1.configure(text=now)
        self.after(1000, lambda: self.update_clock(controller))

class PageAffaire(tk.Frame):
    #constructeur de la page d'acceuil
    def __init__(self, parent, controller):
        tk.Frame.__init__(self,parent)

        #configuration ligne/colonne StartPage
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=4)
        self.rowconfigure(2, weight=1)
        self.rowconfigure(3, weight=1)
        
        #Text general
        tk.Label(self, text="Numero d'affaire", font=LARGE_FONT, justify = CENTER, bg = 'green').grid(column = 0, row = 0, sticky='news')
        tk.Label(self, text="Veuillez scanner un code barre affaire. ", font=LARGE_FONT, justify = CENTER).grid(column = 0, row = 1, sticky='news')

        self.btn1 = Button(self, state = NORMAL, text="Pas de code barre d'affaire ? ", font=LARGE_FONT, width=0, height=0,command=lambda: controller.show_frame(PageAffaire2))
        self.btn1.grid(row=2, column=0, sticky='news')

        self.btn1 = Button(self, state = NORMAL, text="Retour", font=LARGE_FONT, width=0, height=0, background="red",command=lambda: controller.reset())
        self.btn1.grid(row=3, column=0, sticky='news')

class PageAffaire2(tk.Frame):
    #constructeur de la page d'acceuil
    def __init__(self, parent, controller):
        tk.Frame.__init__(self,parent)

        #configuration ligne/colonne StartPage
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=3)
        self.rowconfigure(2, weight=3)
        self.rowconfigure(3, weight=1)
        self.rowconfigure(4, weight=1)

        tk.Label(self, text="Numero d'affaire", font=LARGE_FONT, justify = CENTER, bg = 'green').grid(column = 0,columnspan = 2, row = 0, sticky='news')
        tk.Label(self, text="Veuillez entrer le numero d'affaire ou un commentaire.  ", font=LARGE_FONT, justify = CENTER).grid(column = 0,columnspan = 2, row = 1, sticky='news')        

        self.num_affaire = ttk.Entry(self, width = 15, font=LARGE_FONT)
        self.num_affaire.grid(column = 0,columnspan = 2, row = 2, sticky='we')

        self.btn1 = Button(self, state = NORMAL, text="Valider ", font=LARGE_FONT, width=0, height=0,background="green", command=lambda: self.validation(controller))
        self.btn1.grid(row=4, column=1, sticky='news')

        self.btn1 = Button(self, state = NORMAL, text="Retour", font=LARGE_FONT, width=0, height=0, background="red",command=lambda: controller.reset())
        self.btn1.grid(row=4, column=0, sticky='news')

    def validation(self,controller):

        global id_barcode
        global id_affaire
        id_affaire = self.num_affaire.get()
        controller.frames[PageOne].text_num_affaire.set('Numero d\'affaire: '+ id_affaire) 

        #raz
        self.num_affaire.delete(0,END)
        id_barcode = ''

               
        controller.show_frame(PageOne)

class PageOne(tk.Frame):
    #Constructeur de la page 1
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        #configuration ligne/colonne pageOne
        self.columnconfigure(0, weight=1,minsize = 200)
        self.columnconfigure(1, weight=1,minsize = 200)
        self.columnconfigure(2, weight=1,minsize = 200)
        self.columnconfigure(3, weight=1,minsize = 200)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)
        self.rowconfigure(3, weight=1)
        
        #conteneur d'informations utilisateur
        labelframe_user = LabelFrame(self, text='Informations', font=LARGE_FONT)
        labelframe_user.grid(row=0, column=0,columnspan=2, sticky='news')

        self.text = tk.StringVar()        
        self.label_name=Label(labelframe_user, textvariable=self.text, font=MEDIUM_FONT)
        self.label_name.pack(anchor = 'w')

        self.text_num_affaire = tk.StringVar()        
        self.label_name=Label(labelframe_user, textvariable=self.text_num_affaire, font=MEDIUM_FONT)
        self.label_name.pack(anchor = 'w')

        
        #bouton d'assistance
        self.btn2 = Button(self, state = NORMAL, background="yellow", text="Assistance", font=LARGE_FONT, width=0, height=0,anchor="center", command=lambda: controller.show_frame(PageAssistance))
        self.btn2.grid(row=0, column=3, sticky='news')

        #bouton d'administration
        self.btn1 = Button(self, state = NORMAL, text="Admin", font=LARGE_FONT, width=0, height=0,command=lambda: controller.show_frame(PageAdmin))
        self.btn1.grid(row=0, column=2, sticky='news')

        #TREEVIEW
        self.tree = ttk.Treeview(self, selectmode = "extended", height = 0)
        self.tree["columns"]=("one","two","three","four")
        
        self.tree.column("#0", width="0")
        self.tree.column("one", width="0")
        self.tree.column("two", width="0")
        self.tree.column("three", width="0")
        self.tree.column("four", width="0")
        
        self.tree.heading("one", text="Désignation")
        self.tree.heading("two", text="Conditionnement")
        self.tree.heading("three", text="Quantitée")
        self.tree.heading("four", text="Total")

        self.tree.grid(row=1, column=0,columnspan=3,rowspan=2, sticky='news')
    
        #button_plus = Button(self)
        Button(self, bg = "blue", text='+', font=LARGE_FONT, command=lambda: self.incrementer()).grid(row=1, column=3, sticky='news') 
        
        #button_moins = Button(self)
        Button(self, bg = "blue", text='-', font=LARGE_FONT, command=lambda: self.decrementer()).grid(row=2, column=3, sticky='news')  
        
        #bouton d'annulation
        Button(self, bg = "red", text='Annuler', font=LARGE_FONT,command=lambda: controller.reset()).grid(row=3, column=0, sticky='news')        
        
        #bouton de validation
        Button(self, bg = "green", text='Valider', font=LARGE_FONT, command=lambda: self.validation(controller)).grid(row=3, column=1, sticky='news')
    
    def incrementer(self):
        item = self.tree.selection()[0]
        self.tree.item(item, values = ( self.tree.item(item)['values'][0],
                                        self.tree.item(item)['values'][1],
                                        self.tree.item(item)['values'][2]+1,
                                        (self.tree.item(item)['values'][2]+1)*self.tree.item(item)['values'][1]
                                        ))

    def decrementer(self):
        item = self.tree.selection()[0]
        self.tree.item(item, values = ( self.tree.item(item)['values'][0],
                                        self.tree.item(item)['values'][1],
                                        self.tree.item(item)['values'][2]-1,
                                        (self.tree.item(item)['values'][2]-1)*self.tree.item(item)['values'][1]
                                        ))
        if self.tree.item(item)['values'][2] <= 0:
            self.tree.delete(item)

    #Fonction de validation
    def validation(self,controller):

        global id_affaire
        global mail_magasinier

        for Parent in self.tree.get_children():
            
            reference_materiel = str(self.tree.item(Parent)["text"])            
            designation_materiel = str(self.tree.item(Parent)['values'][0])
            conditionnement_materiel = str(self.tree.item(Parent)['values'][1])
            quantite_materiel = str(self.tree.item(Parent)['values'][2])
            total_materiel = str(self.tree.item(Parent)['values'][3])

            #print("id = "+id_materiel+", designation = "+designation_materiel+", conditionnement = "+conditionnement_materiel+", quantite = "+quantite_materiel+", total ="+total_materiel)

            #ouverture du fichier materiel.xml
            tree = ET.parse(path_prog + 'materiel.xml')
            root = tree.getroot()
            for child in root:
                    reference_bdd = child.get('reference')
                    if reference_bdd == reference_materiel:
                            
                            child.find('stock').text = str(int(child.find('stock').text) - int(total_materiel))
                            
                            fichier = open(path_prog + "log.txt", "a")
                            fichier.write("\nRetrait de "+ str(total_materiel) +" x "+ str(designation_materiel)+"/"+ str(reference_materiel) + " sur l'affaire : "+ id_affaire + ", le " + strftime("%d/%m/%y %H:%M"))
                            fichier.close()
                            
                            #remplissage du fichier sortie.xml
                            tree_sortie_input = ET.parse(path_prog + 'sortie.xml')
                            
                            a1s=tree_sortie_input.getroot()

                            b1s = ET.SubElement(a1s, 'affaire')        
                            b1s.set('numero_affaire', id_affaire)

                            c1s = ET.SubElement(b1s, 'reference')
                            c1s.text = str(reference_materiel)

                            c2s = ET.SubElement(b1s, 'designation')
                            c2s.text = str(designation_materiel)

                            c3 = ET.SubElement(b1s, 'total_unitaire')
                            c3.text = str(total_materiel)

                            c4s = ET.SubElement(b1s, 'nom')
                            c4s.text = id_user

                            c5s = ET.SubElement(b1s, 'date')
                            c5s.text = strftime("%d/%m/%y %H:%M")
                            
                            tree_sortie_output = ET.ElementTree(a1s)
                            tree_sortie_output.write(path_prog + 'sortie.xml')
                            ##########################################################################


                            #Alerte rupture de stock
                            if(child.find('stock').text <= child.find('alerte_fin_stock').text):
                                controller.send_mail(   send_from= mail_systeme,
                                                        subject= "Alerte Rupture " + nom_magasin + ' '  + strftime("%d/%m/%y %H:%M" + " - " + designation_materiel + " / "+ reference_materiel + " - quantite restante = " + child.find('stock').text ) ,
                                                        text="",
                                                        send_to= mail_magasinier,
                                                        files= None)
                                

            tree.write(path_prog + 'materiel.xml')

        #retour a la page d'acceuil
        controller.reset()

class PageInformations(tk.Frame):
    #constructeur de la page d'acceuil
    def __init__(self, parent, controller):
        tk.Frame.__init__(self,parent)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=3)
        self.rowconfigure(2, weight=1)

        LabelFrame_textbox = LabelFrame(self)
        LabelFrame_textbox.grid(column=0,row=1, sticky='news')

        #configuration ligne/colonne StartPage
        LabelFrame_textbox.columnconfigure(0, weight=1)
        LabelFrame_textbox.columnconfigure(1, weight=3)
        LabelFrame_textbox.rowconfigure(0, weight=1)
        LabelFrame_textbox.rowconfigure(1, weight=1)
        LabelFrame_textbox.rowconfigure(2, weight=1)
        LabelFrame_textbox.rowconfigure(3, weight=1)
        LabelFrame_textbox.rowconfigure(4, weight=1)
        
        #Label
        tk.Label(self, text="Ravitaillement", font=LARGE_FONT, bg = 'green').grid(column = 0, row = 0, sticky='news', columnspan = 2)
        tk.Label(LabelFrame_textbox, text="Reference*", font=LARGE_FONT).grid(column = 0, row = 0, sticky='e')
        tk.Label(LabelFrame_textbox, text="quantite*", font=LARGE_FONT).grid(column = 0, row = 1, sticky='e')
        #textbox
        self.entree_reference = ttk.Entry(LabelFrame_textbox, width = 15, font=LARGE_FONT)
        self.entree_reference.grid(column = 1, row = 0, sticky='we')

        self.entree_quantite = ttk.Entry(LabelFrame_textbox, width = 15, font=LARGE_FONT)
        self.entree_quantite.grid(column = 1, row = 1, sticky='we')

        #labelframe pour les boutons
        LabelFrame_bouton = LabelFrame(self)
        LabelFrame_bouton.grid(column=0,row=2,columnspan=2, sticky='news')

        LabelFrame_bouton.columnconfigure(0, weight=1)
        LabelFrame_bouton.columnconfigure(1, weight=1)
        LabelFrame_bouton.rowconfigure(0, weight=1)

        #bouton d'annulation
        Button(LabelFrame_bouton, bg = "red", text='Annuler', font=LARGE_FONT,command=lambda: controller.show_frame(PageAdmin)).grid(column = 0, row = 0, sticky='news')        
        
        #bouton de validation
        Button(LabelFrame_bouton, bg = "green", text='Valider', font=LARGE_FONT,command=lambda: self.validation(controller)).grid(column = 1, row = 0, sticky='news')

    def validation(self,controller):

        reference_materiel = self.entree_reference.get()
        quantite_materiel = self.entree_quantite.get()
        #On verifie que tous les champs sont completes
        if(reference_materiel != '' and quantite_materiel != ''):
            #ratatouille pour le restockage, recheche de la reference puis actualisation du stock

            #ouverture du fichier materiel.xml
            tree = ET.parse(path_prog + 'materiel.xml')
            root = tree.getroot()
            for child in root:
                    reference_bdd = child.get('reference')
                    if reference_materiel == reference_bdd:                            
                            child.find('stock').text = quantite_materiel
            tree.write(path_prog + 'materiel.xml')

            #raz
            self.entree_quantite.delete(0,END)
            self.entree_reference.delete(0,END)

            controller.show_frame(PageAdmin)
        else:
            #erreur, au moins un des champs doit être vide.
            print("erreur : au moins une des zones de texte est vide.")

class PageAdmin(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        #configuration ligne/colonne PageInformations
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)
        self.columnconfigure(3, weight=1)

        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)
        self.rowconfigure(3, weight=1)
        self.rowconfigure(4, weight=0)
        self.rowconfigure(5, weight=1)
        
        #Text general
        self.text = tk.StringVar()
        self.text.set("Page d'administration")
        tk.Label(self, textvariable=self.text, font=LARGE_FONT, justify = CENTER, bg = 'green').grid(column = 0, row = 0,columnspan=4, sticky='news')

        #conteneur d'informations
        #labelframe_status = LabelFrame(self, text='Informations')
        #labelframe_status.grid(row=1, column=0,columnspan=4, sticky='news')

        #bouton d'action
        button_copy = tk.Button(self, text="Ajout de matériel",command=lambda: controller.show_frame(PageAjoutOutil))
        button_copy.grid(row=1, column=0, sticky='news')

        button_copy = tk.Button(self, text="Ajout de personnel",command=lambda: controller.show_frame(PageAjoutPersonnel))
        button_copy.grid(row=1, column=1, sticky='news')

        button_copy = tk.Button(self, text="Ravitaillement",command=lambda: controller.show_frame(PageInformations))
        button_copy.grid(row=1, column=2, sticky='news')

        button_maj_personnel = tk.Button(self, text="MAJ Personnel",command=lambda: self.MAJ_PERSONNEL(controller))
        button_maj_personnel.grid(row=2, column=1, sticky='news')

        button_maj_materiel = tk.Button(self, text="MAJ Materiel",command=lambda: self.MAJ_MATERIEL(controller))
        button_maj_materiel.grid(row=2, column=2, sticky='news')

        button_maj_materiel = tk.Button(self, text="! MAJ CONFIG !",command=lambda: self.MAJ_CONFIG(controller))
        button_maj_materiel.grid(row=2, column=3, sticky='news')

        button_tr_mail = tk.Button(self, text="tr mail",command=lambda:  self.TRANSFERT_MAIL(controller))
        button_tr_mail.grid(row=2, column=0, sticky='news')

        button_reset = tk.Button(self, text="Reset Log",command=lambda:self.RESET_LOG())
        button_reset.grid(row=3, column=0, sticky='news')

        #bouton de sauvegarde des fichier dans le dossier backup
        button_sauvegarde = tk.Button(self, text="Sauvegarde",command=lambda: self.SAUVEGARDE())
        button_sauvegarde.grid(row=3, column=1, sticky='news')

        #bouton de restauration de la dernière sauvegarde
        button_restauration = tk.Button(self, text="Restauration",command=lambda: self.RESTAURATION())
        button_restauration.grid(row=3, column=2, sticky='news')

        #bouton de restauration de la dernière sauvegarde
        button_restauration = tk.Button(self, text="Magasinier",command=lambda: controller.show_frame(Magasinier))
        button_restauration.grid(row=3, column=3, sticky='news')
        
        #bouton nom du magaisn
        button_restauration = tk.Button(self, text="Nom Magasin",command=lambda: controller.show_frame(NomMagasin))
        button_restauration.grid(row=1, column=3, sticky='news')
        
        #bouton retour
        button1 = tk.Button(self, text="Retour",command=lambda: controller.show_frame(PageOne))
        button1.grid(row=5, column=0,columnspan=4, sticky='news')

    def TRANSFERT_MAIL(self, controller):
        #envoi d'un mail avec tout les fichiers en PJ
        global mail_user
        controller.send_mail(send_from= mail_systeme,
        subject= "Sauvegarde " + nom_magasin +" - " + strftime("%d/%m/%y %H:%M"),
        text="",
        send_to= mail_systeme,
        files= [path_prog + 'sortie.xml',path_prog + 'materiel.xml', path_prog + 'personnel.xml', path_prog + 'log.txt', path_prog + 'config.ini'])

    def RESET_LOG(self):
        open(path_prog + 'log.txt', 'w').close()

    def MAJ_PERSONNEL(self, controller):
        # create an IMAP4 class with SSL 
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        # authenticate
        imap.login(mail_systeme, mdp_systeme)

        status, messages = imap.select("INBOX")
        last_message= int(messages[0])

        res, msg = imap.fetch(str(last_message), "(RFC822)")
        for response in msg:
            if isinstance(response, tuple):
                # parse a bytes email into a message object
                msg = email.message_from_bytes(response[1])
                # if the email message is multipart
                if msg.is_multipart():
                    # iterate over email parts
                    for part in msg.walk():
                        # extract content type of email
                        content_disposition = str(part.get("Content-Disposition"))
                        try:
                            # get the email body
                            body = part.get_payload(decode=True).decode()
                        except:
                            pass
                        if "attachment" in content_disposition:
                            # download attachment
                            filename = part.get_filename()
                            if filename:
                                filepath = os.path.join(path_prog, filename)
                                # download attachment and save it
                                if part.get_filename() == "personnel.xml":
                                    open(filepath, "wb").write(part.get_payload(decode=True))
        imap.close()
        imap.logout()

    def MAJ_MATERIEL(self, controller):
        # create an IMAP4 class with SSL 
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        # authenticate
        imap.login(mail_systeme, mdp_systeme)

        status, messages = imap.select("INBOX")
        last_message= int(messages[0])

        res, msg = imap.fetch(str(last_message), "(RFC822)")
        for response in msg:
            if isinstance(response, tuple):
                # parse a bytes email into a message object
                msg = email.message_from_bytes(response[1])
                # if the email message is multipart
                if msg.is_multipart():
                    # iterate over email parts
                    for part in msg.walk():
                        # extract content type of email
                        content_disposition = str(part.get("Content-Disposition"))
                        try:
                            # get the email body
                            body = part.get_payload(decode=True).decode()
                        except:
                            pass
                        if "attachment" in content_disposition:
                            # download attachment
                            filename = part.get_filename()
                            if filename:
                                filepath = os.path.join(path_prog, filename)
                                # download attachment and save it
                                if part.get_filename() == "materiel.xml":
                                    open(filepath, "wb").write(part.get_payload(decode=True))
        imap.close()
        imap.logout()

    def MAJ_CONFIG(self, controller):
        # create an IMAP4 class with SSL 
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        # authenticate
        imap.login(mail_systeme, mdp_systeme)

        status, messages = imap.select("INBOX")
        last_message= int(messages[0])

        res, msg = imap.fetch(str(last_message), "(RFC822)")
        for response in msg:
            if isinstance(response, tuple):
                # parse a bytes email into a message object
                msg = email.message_from_bytes(response[1])
                # if the email message is multipart
                if msg.is_multipart():
                    # iterate over email parts
                    for part in msg.walk():
                        # extract content type of email
                        content_disposition = str(part.get("Content-Disposition"))
                        try:
                            # get the email body
                            body = part.get_payload(decode=True).decode()
                        except:
                            pass
                        if "attachment" in content_disposition:
                            # download attachment
                            filename = part.get_filename()
                            if filename:
                                filepath = os.path.join(path_prog, filename)
                                # download attachment and save it
                                if part.get_filename() == path_prog + "config.ini":
                                    open(filepath, "wb").write(part.get_payload(decode=True))
        imap.close()
        imap.logout()
    
    def RESTAURATION(self):
        try:
            shutil.copy(path_prog + "backup/materiel.xml",path_prog + "materiel.xml")
            shutil.copy(path_prog + "backup/personnel.xml",path_prog + "personnel.xml")
            shutil.copy(path_prog + "backup/config.ini", path_prog + "config.ini")
        except Exception as error:
            print(error)

    def SAUVEGARDE(self):
        if not os.path.isdir("backup/"):
            os.mkdir("backup/")

        shutil.copy(path_prog + "materiel.xml",path_prog + "backup/materiel.xml")
        shutil.copy(path_prog + "personnel.xml",path_prog + "backup/personnel.xml")
        shutil.copy(path_prog + "config.ini",path_prog + "backup/config.ini")

class PageAjoutOutil(tk.Frame):
    #constructeur de la page d'acceuil
    def __init__(self, parent, controller):
        tk.Frame.__init__(self,parent)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=3)
        self.rowconfigure(2, weight=1)

        LabelFrame_textbox = LabelFrame(self)
        LabelFrame_textbox.grid(column=0,row=1, sticky='news')

        #configuration ligne/colonne StartPage
        LabelFrame_textbox.columnconfigure(0, weight=1)
        LabelFrame_textbox.columnconfigure(1, weight=3)
        LabelFrame_textbox.rowconfigure(0, weight=1)
        LabelFrame_textbox.rowconfigure(1, weight=1)
        LabelFrame_textbox.rowconfigure(2, weight=1)
        LabelFrame_textbox.rowconfigure(3, weight=1)
        LabelFrame_textbox.rowconfigure(4, weight=1)
        
        #Label
        tk.Label(self, text="Ajout de matériel", font=LARGE_FONT, bg = 'green').grid(column = 0, row = 0, sticky='news', columnspan = 2)
        tk.Label(LabelFrame_textbox, text="Référence*", font=LARGE_FONT).grid(column = 0, row = 0, sticky='e')
        tk.Label(LabelFrame_textbox, text="Désignation*", font=LARGE_FONT).grid(column = 0, row = 1, sticky='e')
        tk.Label(LabelFrame_textbox, text="Stock*", font=LARGE_FONT).grid(column = 0, row = 2, sticky='e')
        tk.Label(LabelFrame_textbox, text="Conditionnement*", font=LARGE_FONT).grid(column = 0, row = 3, sticky='e')
        tk.Label(LabelFrame_textbox, text="Alerte*", font=LARGE_FONT).grid(column = 0, row = 4, sticky='e')

        #textbox
        self.entree_reference = ttk.Entry(LabelFrame_textbox, width = 15, font=LARGE_FONT)
        self.entree_reference.grid(column = 1, row = 0, sticky='we')

        self.entree_designation = ttk.Entry(LabelFrame_textbox, width = 15, font=LARGE_FONT)
        self.entree_designation.grid(column = 1, row = 1, sticky='we')

        self.entree_stock = ttk.Entry(LabelFrame_textbox, width = 15, font=LARGE_FONT)
        self.entree_stock.grid(column = 1, row = 2, sticky='we')

        self.entree_conditionnement = ttk.Entry(LabelFrame_textbox, width = 15, font=LARGE_FONT)
        self.entree_conditionnement.grid(column = 1, row = 3, sticky='we')

        self.entree_alerte = ttk.Entry(LabelFrame_textbox, width = 15, font=LARGE_FONT)
        self.entree_alerte.grid(column = 1, row = 4, sticky='we')

        #labelframe pour les boutons
        LabelFrame_bouton = LabelFrame(self)
        LabelFrame_bouton.grid(column=0,row=2,columnspan=2, sticky='news')

        LabelFrame_bouton.columnconfigure(0, weight=1)
        LabelFrame_bouton.columnconfigure(1, weight=1)
        LabelFrame_bouton.rowconfigure(0, weight=1)

        #bouton d'annulation
        Button(LabelFrame_bouton, bg = "red", text='Annuler', font=LARGE_FONT,command=lambda: controller.show_frame(PageAdmin)).grid(column = 0, row = 0, sticky='news')        
        
        #bouton de validation
        Button(LabelFrame_bouton, bg = "green", text='Valider', font=LARGE_FONT,command=lambda: self.validation(controller)).grid(column = 1, row = 0, sticky='news')

    def validation(self,controller):       
        #On verifie que tous les champs sont completes.
        if(self.entree_reference.get() != '' and self.entree_designation.get() != '' and self.entree_stock.get() != '' and self.entree_conditionnement.get() != '' and self.entree_alerte.get() != ''):
            #remplissage du fichier materiel.xml
            tree = ET.parse(path_prog + 'materiel.xml')
            
            a=tree.getroot()

            b = ET.SubElement(a, 'materiel')        
            b.set('reference', str(self.entree_reference.get()))

            c1 = ET.SubElement(b, 'designation')
            c1.text = str(self.entree_designation.get())

            c2 = ET.SubElement(b, 'stock')
            c2.text = str(self.entree_stock.get())

            c3 = ET.SubElement(b, 'quantite_minimum_de_sortie')
            c3.text = str(self.entree_conditionnement.get())

            c4 = ET.SubElement(b, 'alerte_fin_stock')
            c4.text = str(self.entree_alerte.get())
            
            tree2 = ET.ElementTree(a)
            tree2.write(path_prog + 'materiel.xml')

            #raz
            self.entree_reference.delete(0,END)
            self.entree_designation.delete(0,END)
            self.entree_conditionnement.delete(0,END)
            self.entree_stock.delete(0,END)
            self.entree_alerte.delete(0,END)

            controller.show_frame(PageAdmin)
        else:
            #erreur, au moins un des champs doit être vide.
            print("erreur : au moins une des zones de texte est vide.")

class PageAjoutPersonnel(tk.Frame):
    #constructeur de la page d'acceuil
    def __init__(self, parent, controller):
        tk.Frame.__init__(self,parent)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=3)
        self.rowconfigure(2, weight=1)

        LabelFrame_textbox = LabelFrame(self)
        LabelFrame_textbox.grid(column=0,row=1, sticky='news')

        #configuration ligne/colonne StartPage
        LabelFrame_textbox.columnconfigure(0, weight=1)
        LabelFrame_textbox.columnconfigure(1, weight=3)
        LabelFrame_textbox.rowconfigure(0, weight=1)
        LabelFrame_textbox.rowconfigure(1, weight=1)
        LabelFrame_textbox.rowconfigure(2, weight=1)
        LabelFrame_textbox.rowconfigure(3, weight=1)
        LabelFrame_textbox.rowconfigure(4, weight=1)
        
        #Label
        tk.Label(self, text="Ajout de personnel", font=LARGE_FONT, bg = 'green').grid(column = 0, row = 0, sticky='news', columnspan = 2)
        tk.Label(LabelFrame_textbox, text="Nom", font=LARGE_FONT).grid(column = 0, row = 0, sticky='e')
        tk.Label(LabelFrame_textbox, text="Mail", font=LARGE_FONT).grid(column = 0, row = 1, sticky='e')
        tk.Label(LabelFrame_textbox, text="Identifiant", font=LARGE_FONT).grid(column = 0, row = 2, sticky='e')

        #textbox
        self.entree_name = ttk.Entry(LabelFrame_textbox, width = 15, font=LARGE_FONT)
        self.entree_name.grid(column = 1, row = 0, sticky='we')

        self.entree_mail = ttk.Entry(LabelFrame_textbox, width = 15, font=LARGE_FONT)
        self.entree_mail.grid(column = 1, row = 1, sticky='we')

        self.entree_identifiant = ttk.Entry(LabelFrame_textbox, width = 15, font=LARGE_FONT)
        self.entree_identifiant.grid(column = 1, row = 2, sticky='we')

        #labelframe pour les boutons
        LabelFrame_bouton = LabelFrame(self)
        LabelFrame_bouton.grid(column=0,row=2,columnspan=2, sticky='news')

        LabelFrame_bouton.columnconfigure(0, weight=1)
        LabelFrame_bouton.columnconfigure(1, weight=1)
        LabelFrame_bouton.rowconfigure(0, weight=1)

        #bouton d'annulation
        Button(LabelFrame_bouton, bg = "red", text='Annuler', font=LARGE_FONT,command=lambda: controller.show_frame(PageAdmin)).grid(column = 0, row = 0, sticky='news')        
        
        #bouton de validation
        Button(LabelFrame_bouton, bg = "green", text='Valider', font=LARGE_FONT,command=lambda: self.validation(controller)).grid(column = 1, row = 0, sticky='news')

    def validation(self,controller):
        #On verifie que tous les champs sont completes
        if(self.entree_identifiant.get() != '' and self.entree_name.get() != '' and self.entree_mail.get() != ''):
            #remplissage du fichier materiel.xml
            tree = ET.parse(path_prog + 'personnel.xml')
            
            a=tree.getroot()

            b = ET.SubElement(a, 'personnel')        
            b.set('id', str(self.entree_identifiant.get()))

            c1 = ET.SubElement(b, 'name')
            c1.text = str(self.entree_name.get())

            c2 = ET.SubElement(b, 'auth')
            c2.text = "utilisateur"

            c3 = ET.SubElement(b, 'mail')
            c3.text = str(self.entree_mail.get())
            
            tree2 = ET.ElementTree(a)
            tree2.write(path_prog + 'personnel.xml')

            #raz
            self.entree_mail.delete(0,END)
            self.entree_identifiant.delete(0,END)
            self.entree_name.delete(0,END)

            controller.show_frame(PageAdmin)
        else:
            #erreur, au moins un des champs doit être vide.
            print("erreur : au moins une des zones de texte est vide.")

class PageAssistance(tk.Frame):
    #constructeur de la page d'acceuil
    def __init__(self, parent, controller):
        tk.Frame.__init__(self,parent)

        #configuration ligne/colonne StartPage
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        #MODIFS APRES PORGRAMME FONCTIONNEL
        #self.rowconfigure(1, weight=3)
        #MODIFS APRES PORGRAMME FONCTIONNEL
        #self.rowconfigure(2, weight=1)
        
        #MODIFS APRES PORGRAMME FONCTIONNEL
        self.rowconfigure(1, weight=1)
        #MODIFS APRES PORGRAMME FONCTIONNEL
        self.rowconfigure(2, weight=1)
        #MODIFS APRES PORGRAMME FONCTIONNEL
        self.rowconfigure(3, weight=1)
        #MODIFS APRES PORGRAMME FONCTIONNEL
        self.rowconfigure(4, weight=1)
        
        
        tk.Label(self, text="Page d'assistance", font=LARGE_FONT, justify = CENTER, bg = 'green').grid(column = 0, row = 0, sticky='news')       
        
 
      
        #bouton d'annulation
        #Button(self, text='Retour', font=LARGE_FONT,command=lambda: controller.show_frame(PageOne)).grid(column = 0, row = 2, sticky='news')
        
        #MODIFS APRES PORGRAMME FONCTIONNEL
        #bouton d'annulation
        Button(self, text='Retour', font=LARGE_FONT,command=lambda: controller.show_frame(PageOne)).grid(column = 0, row = 4, sticky='news')
        #bouton contact
        Button(self, text='Contact', font=LARGE_FONT,command=lambda: controller.show_frame(Contact)).grid(column = 0, row = 1, sticky='news')
        #questions récurentes
        Button(self, text='Questions', font=LARGE_FONT,command=lambda: controller.show_frame(Questions)).grid(column = 0, row =2 , sticky='news')

#MODIFS APRES PORGRAMME FONCTIONNEL
class Questions(tk.Frame):
    #constructeur de la page d'acceuil
    def __init__(self, parent, controller):
        tk.Frame.__init__(self,parent)
        #configuration ligne/colonne StartPage
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)
        self.rowconfigure(3, weight=1)
        self.rowconfigure(4, weight=1)
        
        Button(self, text='Questions', font=LARGE_FONT,command=lambda: controller.show_frame(Questions)).grid(column = 0, row =0 , sticky='news')
        Button(self, text='Questions', font=LARGE_FONT,command=lambda: controller.show_frame(Questions)).grid(column = 0, row =1 , sticky='news')
        Button(self, text='Questions', font=LARGE_FONT,command=lambda: controller.show_frame(Questions)).grid(column = 0, row =2 , sticky='news')
        Button(self, text='Questions', font=LARGE_FONT,command=lambda: controller.show_frame(Questions)).grid(column = 0, row =3 , sticky='news')
        Button(self, text='Retour', font=LARGE_FONT,command=lambda: controller.show_frame(PageAssistance)).grid(column = 0, row = 4, sticky='news')

#MODIFS APRES PORGRAMME FONCTIONNEL
class Contact(tk.Frame):
    #constructeur de la page d'acceuil
    def __init__(self, parent, controller):
        tk.Frame.__init__(self,parent)
        #configuration ligne/colonne StartPage
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=5)
        
        Button(self, text='Retour', font=LARGE_FONT,command=lambda: controller.show_frame(PageAssistance)).grid(column = 0, row = 4, sticky='news')

class Magasinier(tk.Frame):
    #constructeur de la page d'acceuil
    def __init__(self, parent, controller):
        tk.Frame.__init__(self,parent)

        #configuration ligne/colonne StartPage
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=3)
        self.rowconfigure(2, weight=3)
        self.rowconfigure(3, weight=1)
        self.rowconfigure(4, weight=1)

        tk.Label(self, text="Magasinier", font=LARGE_FONT, justify = CENTER, bg = 'green').grid(column = 0, row = 0, sticky='news')
        tk.Label(self, text="Adresse mail du magasinier : ", font=LARGE_FONT, justify = CENTER).grid(column = 0, row = 1, sticky='news')        

        self.nouveau_mail = ttk.Entry(self, width = 15, font=LARGE_FONT)
        self.nouveau_mail.grid(column = 0, row = 2, sticky='we')

        self.btn1 = Button(self, state = NORMAL, text="Valider ", font=LARGE_FONT, width=0, height=0,background="green",command=lambda: self.validation(controller))
        self.btn1.grid(row=3, column=0, sticky='news')

        self.btn1 = Button(self, state = NORMAL, text="Retour", font=LARGE_FONT, width=0, height=0, background="red",command=lambda: controller.show_frame(PageAdmin))
        self.btn1.grid(row=4, column=0, sticky='news')

    def validation(self,controller):
        #ici on modifira l'adresse mail du magasinier
        global mail_magasinier
        global id_barcode

        mail_magasinier = self.nouveau_mail.get()
        print(mail_magasinier)

        self.nouveau_mail.delete(0,END)
        id_barcode = ''

        config = configparser.ConfigParser()
        config.read(path_prog + 'config.ini')        
        config.set('parametre', 'mail_magasinier', mail_magasinier)

        with open(path_prog + 'config.ini', 'w') as configfile:
            config.write(configfile)

        controller.reset()
        
class NomMagasin(tk.Frame):
    #constructeur de la page d'acceuil
    def __init__(self, parent, controller):
        tk.Frame.__init__(self,parent)

        #configuration ligne/colonne StartPage
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=3)
        self.rowconfigure(2, weight=3)
        self.rowconfigure(3, weight=1)
        self.rowconfigure(4, weight=1)

        tk.Label(self, text="Nom du Magasin", font=LARGE_FONT, justify = CENTER, bg = 'green').grid(column = 0, row = 0, sticky='news')
        tk.Label(self, text="Nouveau nom du magasin* ", font=LARGE_FONT, justify = CENTER).grid(column = 0, row = 1, sticky='news')        

        self.nouveau_nom_magasin = ttk.Entry(self, width = 15, font=LARGE_FONT)
        self.nouveau_nom_magasin.grid(column = 0, row = 2, sticky='we')

        self.btn1 = Button(self, state = NORMAL, text="Valider ", font=LARGE_FONT, width=0, height=0,background="green",command=lambda: self.validation(controller))
        self.btn1.grid(row=3, column=0, sticky='news')

        self.btn1 = Button(self, state = NORMAL, text="Retour", font=LARGE_FONT, width=0, height=0, background="red",command=lambda: controller.show_frame(PageAdmin))
        self.btn1.grid(row=4, column=0, sticky='news')

    def validation(self,controller):
        #ici on modifira le nom du magasin
        global nom_magasin
        global path_prog

        nom_magasin = self.nouveau_nom_magasin.get()

        config = configparser.ConfigParser()
        config.read(path_prog + 'config.ini')        
        config.set('parametre', 'nom_magasin', nom_magasin)

        with open(path_prog + 'config.ini', 'w') as configfile:
            config.write(configfile)

        controller.reset()

#ouverture du fichier de configuration
config = configparser.ConfigParser()
config.read(path_prog + 'config.ini')

#recuperation des données du fichier config.ini
mail_magasinier = config.get('parametre', 'mail_magasinier')
nom_magasin = config.get('parametre',       'nom_magasin')
mail_systeme = config.get('parametre', 'mail_systeme')
default_address = config.get('parametre', 'mail_systeme')
mdp_systeme = config.get('parametre', 'mdp_systeme')
id_admin = config.get('parametre', 'id_admin')

#Demarage du programme
app = SeaofBTCapp()
app.mainloop()
