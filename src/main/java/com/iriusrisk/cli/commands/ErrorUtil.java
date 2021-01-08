package com.iriusrisk.cli.commands;

import picocli.CommandLine;

public class ErrorUtil {

    /**
     * Throws an API error.
     *
     * @param spec the CommandSpec, used for writing to command line.
     */
    public static void apiError(CommandLine.Model.CommandSpec spec, String message) {
        throw new CommandLine.ParameterException(spec.commandLine(),
                message == null ? "Error while calling API" : message);
    }

    /**
     * Throws an error indicating the absence of the API token.
     *
     * @param spec the CommandSpec, used for writing to command line.
     */
    public static void apiTokenError(CommandLine.Model.CommandSpec spec) {
        throw new CommandLine.ParameterException(spec.commandLine(), "No API token found. To configure your API token please use command:\n" +
                "  irius configure token set <api token>\n" +
                "If you do not have an api token please contact your administrator.\n");
    }

    /**
     * Throws a "missing subcommand" error.
     *
     * @param spec the CommandSpec, used for writing to command line.
     */
    public static void subcommandError(CommandLine.Model.CommandSpec spec) {
        throw new CommandLine.ParameterException(spec.commandLine(), "Missing required subcommand");
    }

    /**
     * Throws a custom error.
     *
     * @param spec    the CommandSpec, used for writing to command line.
     * @param message the message
     */
    public static void customError(CommandLine.Model.CommandSpec spec, String message) {
        throw new CommandLine.ParameterException(spec.commandLine(), message);
    }
}
