package com.iriusrisk.cli.commands.configure;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.iriusrisk.cli.Irius;
import com.iriusrisk.cli.commands.ErrorUtil;
import picocli.CommandLine;

import java.io.*;
import java.nio.file.Paths;

public class CredentialUtils {

    /**
     * Writes the API token to the credentials.
     *
     * @param token the token value
     */
    public static void writeTokenCredential(String token) throws IOException {
        Credentials credentials = CredentialUtils.createCredentials();
        credentials.setApiToken(token);

        CredentialUtils.writeCredentials(credentials);
    }

    /**
     * Creates the credentials file. The location is specified by {@link Irius#getIriusPath()}.
     * The method returns the credentials file.
     *
     * @return the credentials
     * @throws IOException if an error occurs while creating the credentials file
     */
    public static Credentials createCredentials() throws IOException {
        String iriusPath = Irius.getIriusPath();
        File iriusDirectory = new File(iriusPath);

        String credentialsPath = iriusPath + File.separator + Irius.getCredentialsFile();
        File credentialsFile = new File(credentialsPath);

        if (credentialsFile.exists()) {
            return readCredentials();
        }

        try {
            if (iriusDirectory.exists()) {
                boolean created = credentialsFile.createNewFile();
                if (!created) {
                    throw new IOException();
                }

            } else if (iriusDirectory.mkdirs()) {
                boolean created = credentialsFile.createNewFile();
                if (!created) {
                    throw new IOException();
                }

            } else {
                throw new IOException();
            }

        } catch (IOException e) {
            throw new IOException("Error creating the credentials file");
        }

        return readCredentials();
    }

    /**
     * Writes the given credential to the credentials file.
     *
     * @param credentials the credentials
     * @throws IOException if an error occurs while writing to the file
     */
    public static void writeCredentials(Credentials credentials) throws IOException {
        String iriusPath = Irius.getIriusPath();
        String credentialsPath = iriusPath + File.separator + Irius.getCredentialsFile();

        ObjectMapper jackson = new ObjectMapper();
        jackson.writeValue(Paths.get(credentialsPath).toFile(), credentials);
    }

    /**
     * Reads and returns all available credentials.
     */
    public static Credentials readCredentials() {
        String credentialsPath = Irius.getIriusPath() + File.separator + Irius.getCredentialsFile();

        ObjectMapper jackson = new ObjectMapper();
        try {
            return jackson.readValue(Paths.get(credentialsPath).toFile(), Credentials.class);
        } catch (IOException e) {
            return new Credentials();
        }
    }

    /**
     * Checks if the API token exists.
     *
     * @param spec the command spec
     */
    public static void checkToken(CommandLine.Model.CommandSpec spec) {
        if (Irius.getApiToken() == null) {
            ErrorUtil.apiTokenError(spec);
        }
    }
}
