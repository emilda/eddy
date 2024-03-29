/*
 * Copyright (c) 2010-2011, Monash e-Research Centre
 * (Monash University, Australia)
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 * 	* Redistributions of source code must retain the above copyright
 * 	  notice, this list of conditions and the following disclaimer.
 * 	* Redistributions in binary form must reproduce the above copyright
 * 	  notice, this list of conditions and the following disclaimer in the
 * 	  documentation and/or other materials provided with the distribution.
 * 	* Neither the name of the Monash University nor the names of its
 * 	  contributors may be used to endorse or promote products derived from
 * 	  this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY
 * EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
 * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY
 * DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 * (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
 * SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */
package au.edu.monash.merc.capture.struts2.action;

import java.awt.image.BufferedImage;
import java.io.File;

import javax.imageio.ImageIO;

import org.apache.commons.lang.StringUtils;
import org.apache.log4j.Logger;
import org.springframework.context.annotation.Scope;
import org.springframework.stereotype.Controller;

import au.edu.monash.merc.capture.domain.Avatar;

@Scope("prototype")
@Controller("admin.jcropImageAction")
public class JCropImageAction extends ImageUploadAction {

	private int imageX1;

	private int imageY1;

	private int imageX2;

	private int imageY2;

	private int imageW;

	private int imageH;

	private String userImageName;

	private Logger logger = Logger.getLogger(this.getClass().getName());

	public String showImageUpload() {
		try {
			user = retrieveLoggedInUser();
		} catch (Exception e) {
			logger.error(e);
			addActionError(getText("show.profile.image.upload.page.error"));
			return ERROR;
		}
		return SUCCESS;
	}

	public String uploadImage() {

		try {
			user = retrieveLoggedInUser();

			userImageName = "imageUpload" + File.separator + "image_" + user.getId() + ".jpg";

			String destFile = getAppRoot() + userImageName;
			uploadImageFile(destFile, 480, 480);
			int w = getImgWidth();
			int h = getImgHeight();
			if ((w < 48) || h < 48) {
				addFieldError("imageFileSize", getText("profile.image.size.too.small"));
				return INPUT;
			}
		} catch (Exception e) {
			logger.error(e);
			addActionError(getText("profile.image.file.upload.failed"));
			return ERROR;
		}
		return SUCCESS;
	}

	public void validateUploadImage() {

		if (StringUtils.isBlank(getImageFileName())) {
			addFieldError("uploadFileName", getText("profile.image.file.must.be.provided"));
			return;
		}

		if (!(StringUtils.containsIgnoreCase(getImageFileName(), "jpg")) && !(StringUtils.containsIgnoreCase(getImageFileName(), "png"))
				&& !(StringUtils.containsIgnoreCase(getImageFileName(), "gif"))) {
			addFieldError("fileFormateError", getText("profile.image.format.not.supported"));
			return;
		}
	}

	public String saveAvatar() {
		try {
			user = retrieveLoggedInUser();
			Avatar avatar = user.getAvatar();

			String avatarFile = "avatar" + File.separator + "image_" + user.getId() + ".jpg";
			avatar.setFileName(avatarFile);

			String srcImageFile = getAppRoot() + userImageName;

			BufferedImage bufImage = ImageIO.read(new File(srcImageFile));

			if (imageX1 < 0) {
				imageX1 = 0;
			}
			if (imageY1 < 0) {
				imageY1 = 0;
			}
			// set the final scale image size;
			int scaleW = 48;
			int scaleH = 48;
			if (imageX2 < imageW) {
				imageW = imageX2;
				scaleW = imageX2;
			}
			if (imageY2 < imageH) {
				imageH = imageY2;
				scaleH = imageY2;
			}

			BufferedImage cropImage = bufImage.getSubimage(imageX1, imageY1, imageW, imageH);
			String destFile = getAppRoot() + avatarFile;

			cropImage(cropImage, destFile, scaleW, scaleH);
			avatar.setFileType("jpg");
			avatar.setCustomized(true);

			this.dmService.updateAvatar(avatar);

			// saveInSession(ActConstants.SESSION_AVATAR_URL, avatar.getFileName());

		} catch (Exception e) {
			logger.error(e);
			addActionError(getText("profile.image.file.saving.failed"));
			return ERROR;
		}
		return SUCCESS;
	}

	public int getImageX1() {
		return imageX1;
	}

	public void setImageX1(int imageX1) {
		this.imageX1 = imageX1;
	}

	public int getImageY1() {
		return imageY1;
	}

	public void setImageY1(int imageY1) {
		this.imageY1 = imageY1;
	}

	public int getImageX2() {
		return imageX2;
	}

	public void setImageX2(int imageX2) {
		this.imageX2 = imageX2;
	}

	public int getImageY2() {
		return imageY2;
	}

	public void setImageY2(int imageY2) {
		this.imageY2 = imageY2;
	}

	public int getImageW() {
		return imageW;
	}

	public void setImageW(int imageW) {
		this.imageW = imageW;
	}

	public int getImageH() {
		return imageH;
	}

	public void setImageH(int imageH) {
		this.imageH = imageH;
	}

	public String getUserImageName() {
		return userImageName;
	}

	public void setUserImageName(String userImageName) {
		this.userImageName = userImageName;
	}

}
