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
package au.edu.monash.merc.capture.util.rights;

import java.io.Serializable;

public class CCLicense implements Serializable {
	private String licenseName;

	private String licenseURI;

	private String licenseHtml;

	private String licenseHrefText;

	public CCLicense() {

	}

	public CCLicense(String licenseName, String licenseURI, String licenseHtml, String licenseHrefText) {
		super();
		this.licenseName = licenseName;
		this.licenseURI = licenseURI;
		this.licenseHtml = licenseHtml;
		this.licenseHrefText = licenseHrefText;
	}

	public String getLicenseName() {
		return licenseName;
	}

	public void setLicenseName(String licenseName) {
		this.licenseName = licenseName;
	}

	public String getLicenseURI() {
		return licenseURI;
	}

	public void setLicenseURI(String licenseURI) {
		this.licenseURI = licenseURI;
	}

	public String getLicenseHtml() {
		return licenseHtml;
	}

	public void setLicenseHtml(String licenseHtml) {
		this.licenseHtml = licenseHtml;
	}

	public String getLicenseHrefText() {
		return licenseHrefText;
	}

	public void setLicenseHrefText(String licenseHrefText) {
		this.licenseHrefText = licenseHrefText;
	}
}
