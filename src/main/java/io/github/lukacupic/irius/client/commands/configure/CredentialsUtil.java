package io.github.lukacupic.irius.client.commands.configure;

import io.github.lukacupic.irius.client.Irius;

import java.io.*;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Properties;

public class CredentialsUtil {

    /**
     * Attemps to add the given credential to the credentials file.
     *
     * @param name  the credential name
     * @param value the credential value
     */
    public static void addCredential(String name, String value) throws IOException {
        CredentialsUtil.createCredentials();
        CredentialsUtil.writeCredential(name, value);
    }

    /**
     * Creates the credentials file. If the file already exists, the method does nothing.
     * The location is specified by {@link Irius#getIriusPath()}.
     *
     * @throws IOException if an error occurs while creating the credentials file
     */
    public static void createCredentials() throws IOException {
        String iriusPath = Irius.getInstance().getIriusPath();
        File iriusDirectory = new File(iriusPath);

        String credentialsPath = iriusPath + File.separator + "credentials";
        File credentialsFile = new File(credentialsPath);

        if (credentialsFile.exists()) return;

        try {
            if (iriusDirectory.exists()) {
                boolean created = credentialsFile.createNewFile();
                if (!created) throw new IOException();

            } else if (iriusDirectory.mkdirs()) {
                boolean created = credentialsFile.createNewFile();
                if (!created) throw new IOException();

            } else {
                throw new IOException();
            }

        } catch (IOException e) {
            throw new IOException("Error creating the credentials file");
        }
    }

    /**
     * Writes the given credential to the credentials file.
     *
     * @param name  the credential name
     * @param value the credential value
     * @throws IOException if an error occurs while writing to the file
     */
    public static void writeCredential(String name, String value) throws IOException {
        String iriusPath = Irius.getInstance().getIriusPath();
        String credentialsPath = iriusPath + File.separator + "credentials";
        File credentialsFile = new File(credentialsPath);

        FileWriter writer = new FileWriter(credentialsFile, true);
        if (credentialsFile.length() != 0) {
            writer.append(System.lineSeparator());
        }
        writer.append(String.format("%s: %s", name, value));
        writer.flush();
        writer.close();
    }

    /**
     * Attempts to read the given credential from the credentials file.
     * If the credential is not found, the method returns null.
     */
    public static String readCredential(String name) {
        Map<String, String> credentials = readCredentials();
        return credentials == null ? null : credentials.get(name);
    }

    /**
     * Reads and returns all available credentials.
     */
    public static Map<String, String> readCredentials() {
        String credentialsPath = Irius.getInstance().getIriusPath() + File.separator + "credentials";

        try (InputStream input = new FileInputStream(credentialsPath)) {
            Properties prop = new Properties();
            prop.load(input);

            Map<String, String> map = new LinkedHashMap<>();
            for (String name : prop.stringPropertyNames()) {
                map.put(name, prop.getProperty(name));
            }

            return map;

        } catch (IOException io) {
            return null;
        }
    }
}
