package com.iriusrisk.cli.commands.configure;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.iriusrisk.cli.commands.ErrorUtil;
import picocli.CommandLine;

@CommandLine.Command(name = "configure", description = "Manage configuration properties", subcommands = {
        TokenCommand.class
})
public class ConfigureCommand implements Runnable {

    /**
     * Command line Spec for handling missing subcommands.
     */
    @CommandLine.Spec private CommandLine.Model.CommandSpec spec;

    /**
     * Constructor.
     */
    public ConfigureCommand() {
    }

    @CommandLine.Command(name = "list", description = "List all products")
    void listCommand() {
        CredentialUtils.checkToken(spec);

        Credentials credentials = CredentialUtils.readCredentials();
        if (credentials == null) {
            ErrorUtil.customError(spec, "Error while reading credentials. Does the file exist?");
        }

        try {
            ObjectMapper jackson = new ObjectMapper();
            System.out.println(jackson.writeValueAsString(credentials));

        } catch (JsonProcessingException e) {
            ErrorUtil.customError(spec, "Error while printing the credentials.");
        }
    }

    @Override
    public void run() {
        ErrorUtil.subcommandError(spec);
    }
}