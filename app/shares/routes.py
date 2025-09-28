"""Network shares routes"""
from __future__ import annotations
from typing import Union, Dict, List, Any, Tuple
from flask import render_template, request, jsonify, flash, redirect, url_for, Response
from flask_login import login_required, current_user
from app.shares import bp
from app.shares.protocols import get_protocol_manager
from app.models import Share, Dataset, ShareProtocol, ShareStatus, SystemLog, LogLevel, UserRole
from app import db
from datetime import datetime
from app.utils.error_handler import (
    secure_route,
    validate_input,
    log_sensitive_operation,
    DatabaseErrorHandler,
)
from app.utils.atomic_operations import AtomicFileOperations
from app.security.hardening import InputSanitizer


@bp.route("/")
@login_required
def index() -> str:
    """Shares overview page"""
    page = request.args.get("page", 1, type=int)
    shares = Share.query.paginate(page=page, per_page=20, error_out=False)

    # Statistics
    total_shares = Share.query.count()
    active_shares = Share.query.filter_by(status=ShareStatus.ACTIVE).count()

    return render_template(
        "shares/index.html", shares=shares, total_shares=total_shares, active_shares=active_shares
    )


@bp.route("/create", methods=["GET", "POST"])
@login_required
@secure_route
@log_sensitive_operation("share_creation", "network_share")
@validate_input(
    name=lambda x: InputSanitizer.sanitize_filename(x) == x and len(x) >= 3,
    protocol=lambda x: x in ["smb", "nfs", "ftp", "sftp"],
)
def create() -> Union[str, Response]:
    """Create new network share"""
    if not current_user.is_admin():
        flash("Administrator privileges required to create shares", "danger")
        return redirect(url_for("shares.index"))

    if request.method == "POST":
        try:
            name = request.form.get("name", "").strip()
            protocol = ShareProtocol(request.form.get("protocol"))
            dataset_id_str = request.form.get("dataset_id")
            dataset_id = int(dataset_id_str) if dataset_id_str else None
            guest_access = request.form.get("guest_access") == "on"
            read_only = request.form.get("read_only") == "on"
            allowed_hosts = request.form.get("allowed_hosts", "").strip()

            # Validation
            if not name:
                flash("Share name is required", "danger")
                return redirect(url_for("shares.create"))

            if Share.query.filter_by(name=name).first():
                flash("Share name already exists", "danger")
                return redirect(url_for("shares.create"))

            if not dataset_id:
                flash("Dataset selection is required", "danger")
                return redirect(url_for("shares.create"))

            dataset = Dataset.query.get(dataset_id)
            if not dataset:
                flash("Invalid dataset selected", "danger")
                return redirect(url_for("shares.create"))

            # Create share record
            share = Share(
                name=name,
                protocol=protocol,
                dataset_id=dataset_id,
                owner_id=current_user.id,
                guest_access=guest_access,
                read_only=read_only,
                status=ShareStatus.INACTIVE,
                created_by_id=current_user.id,
            )

            # Set allowed hosts
            if allowed_hosts:
                hosts = [host.strip() for host in allowed_hosts.split(",")]
                share.set_allowed_hosts(hosts)

            db.session.add(share)
            db.session.flush()  # Get share ID

            # Create protocol-specific configuration
            protocol_manager = get_protocol_manager(protocol)
            if protocol_manager:
                success, message = (
                    protocol_manager.create_smb_share(share)
                    if protocol == ShareProtocol.SMB
                    else protocol_manager.create_nfs_share(share)
                    if protocol == ShareProtocol.NFS
                    else protocol_manager.create_ftp_share(share)
                )

                if success:
                    share.status = ShareStatus.ACTIVE
                    success_db, error = DatabaseErrorHandler.safe_commit()
                    if not success_db:
                        db.session.rollback()
                        flash(f"Share created but failed to save status: {error}", "warning")
                        return redirect(url_for("shares.create"))

                    SystemLog.log_event(
                        level=LogLevel.INFO,
                        category="shares",
                        message=f"Share created: {name} ({protocol.value}) by {current_user.username}",
                        user_id=current_user.id,
                        ip_address=request.remote_addr,
                        details={
                            "share_id": share.id,
                            "protocol": protocol.value,
                            "dataset": dataset.name,
                        },
                    )

                    flash(f'Share "{name}" created successfully', "success")
                    return redirect(url_for("shares.index"))
                else:
                    db.session.rollback()
                    flash(f"Failed to create share: {message}", "danger")
                    return redirect(url_for("shares.create"))
            else:
                db.session.rollback()
                flash("Unsupported share protocol", "danger")
                return redirect(url_for("shares.create"))

        except Exception as e:
            db.session.rollback()
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category="shares",
                message=f"Failed to create share: {str(e)}",
                user_id=current_user.id,
                ip_address=request.remote_addr,
            )
            flash(f"Error creating share: {str(e)}", "danger")
            return redirect(url_for("shares.create"))

    # GET request - show create form
    datasets = Dataset.query.all()
    protocols = [(p.value, p.value.upper()) for p in ShareProtocol]

    return render_template("shares/create.html", datasets=datasets, protocols=protocols)


@bp.route("/<int:share_id>")
@login_required
def detail(share_id: int) -> str:
    """Share detail page"""
    share = Share.query.get_or_404(share_id)

    # Get protocol-specific connections
    protocol_manager = get_protocol_manager(share.protocol)
    connections = []
    if protocol_manager:
        if share.protocol == ShareProtocol.SMB:
            connections = protocol_manager.get_smb_connections()
        elif share.protocol == ShareProtocol.NFS:
            connections = protocol_manager.get_nfs_connections()
        elif share.protocol == ShareProtocol.FTP:
            connections = protocol_manager.get_ftp_connections()

    return render_template("shares/detail.html", share=share, connections=connections)


@bp.route("/<int:share_id>/toggle", methods=["POST"])
@login_required
@secure_route
@log_sensitive_operation("share_toggle", "network_share")
def toggle(share_id: int) -> Tuple[Response, int]:
    """Toggle share status"""
    if not current_user.is_admin():
        return jsonify({"success": False, "error": "Administrator privileges required"}), 403

    share = Share.query.get_or_404(share_id)

    try:
        protocol_manager = get_protocol_manager(share.protocol)
        if not protocol_manager:
            return jsonify({"success": False, "error": "Unsupported protocol"}), 400

        if share.status == ShareStatus.ACTIVE:
            # Disable share
            success, message = (
                protocol_manager.delete_smb_share(share)
                if share.protocol == ShareProtocol.SMB
                else protocol_manager.delete_nfs_share(share)
                if share.protocol == ShareProtocol.NFS
                else protocol_manager.delete_ftp_share(share)
            )

            if success:
                share.status = ShareStatus.INACTIVE
                action = "disabled"
            else:
                return jsonify({"success": False, "error": message}), 500

        else:
            # Enable share
            success, message = (
                protocol_manager.create_smb_share(share)
                if share.protocol == ShareProtocol.SMB
                else protocol_manager.create_nfs_share(share)
                if share.protocol == ShareProtocol.NFS
                else protocol_manager.create_ftp_share(share)
            )

            if success:
                share.status = ShareStatus.ACTIVE
                action = "enabled"
            else:
                return jsonify({"success": False, "error": message}), 500

        success, error = DatabaseErrorHandler.safe_commit()
        if not success:
            db.session.rollback()
            return jsonify({"success": False, "error": f"Database operation failed: {error}"}), 500

        SystemLog.log_event(
            level=LogLevel.INFO,
            category="shares",
            message=f"Share {action}: {share.name} by {current_user.username}",
            user_id=current_user.id,
            ip_address=request.remote_addr,
            details={"share_id": share.id, "action": action},
        )

        return jsonify(
            {
                "success": True,
                "message": f'Share "{share.name}" {action} successfully',
                "status": share.status.value,
            }
        )

    except Exception as e:
        db.session.rollback()
        SystemLog.log_event(
            level=LogLevel.ERROR,
            category="shares",
            message=f"Error toggling share {share.name}: {str(e)}",
            user_id=current_user.id,
            ip_address=request.remote_addr,
        )
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/<int:share_id>/delete", methods=["POST"])
@login_required
@secure_route
@log_sensitive_operation("share_deletion", "network_share")
def delete(share_id: int) -> Tuple[Response, int]:
    """Delete share"""
    if not current_user.is_admin():
        return jsonify({"success": False, "error": "Administrator privileges required"}), 403

    share = Share.query.get_or_404(share_id)

    try:
        # Remove protocol configuration if active
        if share.status == ShareStatus.ACTIVE:
            protocol_manager = get_protocol_manager(share.protocol)
            if protocol_manager:
                success, message = (
                    protocol_manager.delete_smb_share(share)
                    if share.protocol == ShareProtocol.SMB
                    else protocol_manager.delete_nfs_share(share)
                    if share.protocol == ShareProtocol.NFS
                    else protocol_manager.delete_ftp_share(share)
                )

                if not success:
                    SystemLog.log_event(
                        level=LogLevel.WARNING,
                        category="shares",
                        message=f"Failed to remove protocol config for share {share.name}: {message}",
                        user_id=current_user.id,
                        ip_address=request.remote_addr,
                    )

        # Delete from database
        share_name = share.name
        success, error = DatabaseErrorHandler.safe_delete(share)
        if not success:
            return jsonify({"success": False, "error": f"Database deletion failed: {error}"}), 500

        SystemLog.log_event(
            level=LogLevel.WARNING,
            category="shares",
            message=f"Share deleted: {share_name} by {current_user.username}",
            user_id=current_user.id,
            ip_address=request.remote_addr,
            details={"share_name": share_name},
        )

        return jsonify({"success": True, "message": f'Share "{share_name}" deleted successfully'})

    except Exception as e:
        db.session.rollback()
        SystemLog.log_event(
            level=LogLevel.ERROR,
            category="shares",
            message=f"Error deleting share {share.name}: {str(e)}",
            user_id=current_user.id,
            ip_address=request.remote_addr,
        )
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/connections")
@login_required
def api_connections() -> Response:
    """API endpoint for active connections"""
    connections_summary = {"smb": [], "nfs": [], "ftp": []}

    try:
        # Get SMB connections
        from app.shares.protocols import smb_manager

        connections_summary["smb"] = smb_manager.get_smb_connections()

        # Get NFS connections
        from app.shares.protocols import nfs_manager

        connections_summary["nfs"] = nfs_manager.get_nfs_connections()

        # Get FTP connections
        from app.shares.protocols import ftp_manager

        connections_summary["ftp"] = ftp_manager.get_ftp_connections()

    except Exception as e:
        SystemLog.log_event(
            level=LogLevel.ERROR,
            category="shares",
            message=f"Error getting connection summary: {str(e)}",
        )

    return jsonify(connections_summary)
