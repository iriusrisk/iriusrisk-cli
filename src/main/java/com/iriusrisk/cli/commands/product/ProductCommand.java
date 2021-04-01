package com.iriusrisk.cli.commands.product;

import com.iriusrisk.api.client.ProductsApi;
import com.iriusrisk.api.client.model.CreateProduct;
import com.iriusrisk.api.client.model.Product;
import com.iriusrisk.api.client.model.ProductShort;
import com.iriusrisk.cli.Irius;
import com.iriusrisk.cli.commands.ErrorUtil;
import com.iriusrisk.cli.commands.configure.CredentialUtils;
import com.iriusrisk.iac.CfImport;
import com.iriusrisk.iac.Mode;
import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.Base64;
import org.springframework.web.client.RestClientException;
import picocli.CommandLine;

import java.util.List;

@CommandLine.Command(name = "product", description = "Display product related information")
public class ProductCommand implements Runnable {

  /**
   * Command line Spec for handling missing subcommands.
   */
  @CommandLine.Spec
  private CommandLine.Model.CommandSpec spec;

  /**
   * The Products API.
   */
  private ProductsApi api;

  /**
   * The API token.
   */
  private String token;

  /**
   * Constructor.
   */
  public ProductCommand() {
    this.api = Irius.getApi();
    this.token = Irius.getApiToken();
  }

  @CommandLine.Command(name = "list", description = "List all products")
  void listCommand() {
    CredentialUtils.checkToken(spec);

    try {
      List<ProductShort> products = api.productsGet(token, null, null, null);
      products.forEach(System.out::println);
    } catch (RestClientException e) {
      ErrorUtil.apiError(spec, e.getMessage());
    }
  }

  @CommandLine.Command(name = "show", description = "Display product details")
  void showCommand(@CommandLine.Parameters(paramLabel = "<product unique ID>", description = "Product ID") String id) {
    CredentialUtils.checkToken(spec);

    try {
      Product product = api.productsRefGet(token, id);
      System.out.println(product);
    } catch (RestClientException e) {
      ErrorUtil.apiError(spec, e.getMessage());
    }
  }

  //product create -n productXYZ -i 1382892308 -cf  "/home/vmdovs/NetBeansProjects/cf-import/contentTests/Example4/yaml/Example4.yaml" -mf "/home/vmdovs/NetBeansProjects/cf-import/contentTests/Example4/mapping/iriusrisk-mapping.yaml" -p "CustomerName=My Customer Name,FQDN=domain.com,RemoteAccessCIDR=67.0.8.19/0,VPCID=vpc-f7e21s5s7845s5zc9,PrivateSubnet1ID=subnet-a0246dcd,PrivateSubnet2ID=subnet-a0246dcd4,PublicSubnet1ID= subnet-9bc642ac,PublicSubnet2ID= subnet-9bc742ac,KeyName=SecureKey,DBUrl=db.com,DBPassword=sH34Iyuy238"
  @CommandLine.Command(name = "import", description = "Create a new product in IriusRisk from an external model format. Currently supported types are: AWS CloudFormation.")
  void createCommand(@CommandLine.Option(names = {"-n"}, paramLabel = "<product name>", description = "Product Name") String name,
          @CommandLine.Option(names = {"-type"}, required = true, paramLabel = "<External Model Type>", description = "The External Model type such as 'cf' for AWS CloudFormation") String type,
          @CommandLine.Option(names = {"-i"}, required = true, paramLabel = "<product unique ID>", description = "Product ID") String id,
          @CommandLine.Option(names = {"-f"}, required = true, paramLabel = "<Template>", description = "Template") String template,
          @CommandLine.Option(names = {"-mf"}, paramLabel = "<Mapping File>", description = "Iriusrisk Mapping File") String mapping,
          @CommandLine.Option(names = {"-rmf"}, paramLabel = "<Reference Mapping File>", description = "Iriusrisk Reference Mapping File") String reference,
          @CommandLine.Option(names = {"-gmf"}, paramLabel = "<Generated Mapping File>", description = "Generated Mapping File") String generatedMapping,
          @CommandLine.Option(names = {"-d"}, paramLabel = "<Delete>", description = "Delete product if true") String delete,
          @CommandLine.Option(names = {"-tzw"}, paramLabel = "<TrustZone Width>", description = "TrustZone Width") String trustZoneWidth,
          @CommandLine.Option(names = {"-tzh"}, paramLabel = "<TrustZone Height>", description = "TrustZone Height") String trustZoneHeight,
          @CommandLine.Option(names = {"-gw"}, paramLabel = "<Graph Width>", description = "Graph Width") String graphWidth,
          @CommandLine.Option(names = {"-gh"}, paramLabel = "<Graph Height>", description = "Graph Height") String graphHeight,
          @CommandLine.Option(names = {"-mode"}, paramLabel = "<Mode>", description = "Run the cli in a ttrict or lax mode") String mode,
          @CommandLine.Option(names = {"-p"}, paramLabel = "<Parameters>", description = "Template parameters") String parameters) {

    CredentialUtils.checkToken(spec);

//    System.out.println("name " + name);
//    System.out.println("id " + id);
//    System.out.println("template " + template);
//    System.out.println("mapping " + mapping);
//    System.out.println("parameters " + parameters);
    try {

      if (type.equalsIgnoreCase("cf")) {
        CfImport cfImport = new CfImport();
        cfImport.setTemplateFileName(template);

        if (mode != null && !mode.isEmpty() && mode.equalsIgnoreCase("strict")) {
          cfImport.setMode(Mode.STRICT);
        }
        if (trustZoneWidth != null && !trustZoneWidth.isEmpty()) {
          cfImport.setTrustZoneWidth(Integer.parseInt(trustZoneWidth));
        }
        if (trustZoneHeight != null && !trustZoneHeight.isEmpty()) {
          cfImport.setTrustZoneHeight(Integer.parseInt(trustZoneHeight));
        }
        if (graphHeight != null && !graphHeight.isEmpty()) {
          cfImport.setGraphHeight(Integer.parseInt(graphHeight));
        }

        if (graphWidth != null && !graphWidth.isEmpty()) {
          cfImport.setGraphWidth(Integer.parseInt(graphWidth));
        }

        if (generatedMapping != null && !generatedMapping.isEmpty() &&
                (reference == null || (reference != null && reference.isEmpty()))) {
          System.out.println("Iriusrisk Generated Mapping File is specified with -gmf so"
                  + " the Reference Mapping File is then required to be specified with -rmf");
          System.exit(0);
        }

        if (reference != null && !reference.isEmpty()) {
          cfImport.setReferenceFileName(reference);
          if (generatedMapping != null && !generatedMapping.isEmpty()) {
            cfImport.setGeneratedMappingFileName(generatedMapping);
          } else {
            System.out.println("Auto Generated Iriusrisk Mapping File is not specified with -gmf. Mapping File auto-gen-cf-iriusrisk-mapping.yaml will be auto generated");
            cfImport.setGeneratedMappingFileName("auto-gen-cf-iriusrisk-mapping.yaml");
          }
        } else {
          if (mapping != null && !mapping.isEmpty()) {
            cfImport.setMappingFileName(mapping);
          } else {
            System.out.println("Iriusrisk Mapping File is not provided. Default Mapping File cf-iriusrisk-mapping.yaml is then required");
            cfImport.setMappingFileName(Irius.getIriusPath() + "cf-iriusrisk-mapping.yaml");
          }
        }
        
        if (parameters != null && !parameters.isEmpty()) {
          cfImport.setParameters(parameters);
        }

        cfImport.setDrawIoOutputFileName(Irius.getIriusPath() + "/" + "cf-iriusrisk-output.drawio");
        cfImport.run();
        System.out.println("cfImport.run()");

        CreateProduct cp = new CreateProduct();
        cp.setName(name);
        cp.setRef(id);

        String productXML = createProductXML(id, name, Irius.getIriusPath() + "/" + "cf-iriusrisk-output.drawio");
        Files.write(Paths.get(Irius.getIriusPath() + "/" + "cf-iriusrisk-product.xml"), productXML.getBytes());

        if (delete != null && delete.equalsIgnoreCase("true")) {
          try {
            api.productsRefDelete(token, id);
          } catch (Exception e) {
            System.out.println("Delete product exception " + e.getMessage());
          }
        }
        ProductShort ps = api.productsUploadPost(token, id, name, new File(Irius.getIriusPath() + "/" + "cf-iriusrisk-product.xml"), "STANDARD");

        api.rulesProductRefPut(token, id, "false");

        //This will call https://app.swaggerhub.com/apis/iriusrisk/IriusRisk/1#/Products/post_products_upload
        //to create a new product with the generated draw.io diagram embedded. 
        //AND it should call the API: 
        //https://app.swaggerhub.com/apis/iriusrisk/IriusRisk/1#/Products/put_rules_product__ref_ 
        //which will generate the model associated with the draw.io diagram.
        //should look in the folder ~/.irius for a file called cf-iriusrisk-mapping.yaml t
      } else {
        System.out.println("Product import not supported for type: " + type);
      }
    } catch (RestClientException e) {
      ErrorUtil.apiError(spec, e.getMessage());
    } catch (Exception e) {
      ErrorUtil.apiError(spec, e.getMessage());
    }

  }

  /**
   * Embed the drawio diagram into a product xml
   *
   * @param ref
   * @param name
   * @param drawioFile
   */
  public String createProductXML(String ref, String name, String drawioFile) throws IOException {

    StringBuilder xml = new StringBuilder();
    xml.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>");
    xml.append("<project ref=\"");
    xml.append(ref);
    xml.append("\" name=\"");
    xml.append(name);
    xml.append("\" revision=\"1\" type=\"STANDARD\" status=\"OPEN\" enabled=\"true\" priority=\"0\" tags=\"\" workflowState=\"\">\n");
    xml.append("<desc/><diagram draft=\"true\"><schema>");
    xml.append(Base64.getEncoder().encodeToString(Files.readAllBytes(Paths.get(drawioFile))));
    xml.append("</schema></diagram><trustZones><trustZone ref=\"30c638b5-8620-485c-8d69-aaed40c2b04e\" name=\"Internet\"/>");
    xml.append("</trustZones><questions/><assets/><settings/><dataflows></dataflows><udts></udts><components></components></project>");
    return xml.toString();
  }

  @Override
  public void run() {
    ErrorUtil.subcommandError(spec);
  }
}
