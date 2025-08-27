"""Forms for share management"""
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, BooleanField, IntegerField
from wtforms.validators import DataRequired, Length, Optional, NumberRange
from app.models import ShareProtocol


class ShareForm(FlaskForm):
    """Form for creating and editing network shares"""
    
    name = StringField('Share Name', validators=[
        DataRequired(),
        Length(min=1, max=128, message='Name must be between 1 and 128 characters')
    ], render_kw={'placeholder': 'e.g. documents, media, backup'})
    
    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=500, message='Description must be less than 500 characters')
    ], render_kw={'placeholder': 'Optional description of the share'})
    
    protocol = SelectField('Protocol', validators=[DataRequired()], choices=[
        (ShareProtocol.SMB.value, 'SMB/CIFS'),
        (ShareProtocol.NFS.value, 'NFS'),
        (ShareProtocol.FTP.value, 'FTP')
    ], coerce=str)
    
    path = StringField('Path', validators=[
        DataRequired(),
        Length(min=1, max=500, message='Path must be between 1 and 500 characters')
    ], render_kw={'placeholder': '/mnt/storage/sharename'})
    
    enabled = BooleanField('Enable Share', default=True)
    
    # Access Control
    guest_access = BooleanField('Allow Guest Access', default=False)
    read_only = BooleanField('Read Only', default=False)
    
    # Advanced options (optional)
    max_connections = IntegerField('Max Connections', validators=[
        Optional(),
        NumberRange(min=1, max=1000, message='Max connections must be between 1 and 1000')
    ], default=100)


class ShareEditForm(ShareForm):
    """Form for editing existing shares (inherits from ShareForm)"""
    pass


class ShareProtocolForm(FlaskForm):
    """Form for protocol-specific settings"""
    
    # SMB specific
    smb_workgroup = StringField('Workgroup', validators=[Optional()], 
                               default='WORKGROUP')
    smb_security = SelectField('Security', choices=[
        ('user', 'User Level'),
        ('share', 'Share Level')
    ], default='user')
    
    # NFS specific
    nfs_options = StringField('NFS Options', validators=[Optional()],
                             default='rw,sync,no_subtree_check',
                             render_kw={'placeholder': 'rw,sync,no_subtree_check'})
    
    # FTP specific
    ftp_passive_port_range = StringField('Passive Port Range', validators=[Optional()],
                                       default='10000-10100',
                                       render_kw={'placeholder': '10000-10100'})
    ftp_max_clients = IntegerField('Max Clients', validators=[
        Optional(),
        NumberRange(min=1, max=100)
    ], default=10)