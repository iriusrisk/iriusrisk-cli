package com.iriusrisk.cli.commands.configure;

/**
 * The credentials class.
 */
public class Credentials {

    /**
     * The API token.
     */
    private String apiToken;
    private String url;

    /**
     * Returns the API token.
     *
     * @return the API token
     */
    public String getApiToken() {
        return apiToken;
    }

    /**
     * Sets the APi token.
     *
     * @param apiToken the API token
     */
    public void setApiToken(String apiToken) {
        this.apiToken = apiToken;
    }

    /**
     * Returns the iriusrisk path used by all commands except from configure domain.
     *
      * @return iriusrisk url
     */
    public String getUrl() {
        return url;
    }

    /**
     * Sets the iriusrisk path.
     *
     * @param url iriusrisk url
     */
    public void setUrl(String url) {
        this.url = url;
    }
}