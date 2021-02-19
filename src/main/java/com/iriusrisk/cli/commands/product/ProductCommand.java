package com.iriusrisk.cli.commands.product;

import com.iriusrisk.api.client.ProductsApi;
import com.iriusrisk.api.client.model.CreateProduct;
import com.iriusrisk.api.client.model.Product;
import com.iriusrisk.api.client.model.ProductShort;
import com.iriusrisk.cli.Irius;
import com.iriusrisk.cli.commands.ErrorUtil;
import com.iriusrisk.cli.commands.configure.CredentialUtils;
import com.iriusrisk.iac.CfImport;
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
  @CommandLine.Command(name = "create", description = "Create product from Template")
  void createCommand(@CommandLine.Option(names = {"-n"}, paramLabel = "<product name>", description = "Product Name") String name,
          @CommandLine.Option(names = {"-i"}, paramLabel = "<product unique ID>", description = "Product ID") String id,
          @CommandLine.Option(names = {"-cf"}, paramLabel = "<CF Template>", description = "Cloudformation Template") String template,
          @CommandLine.Option(names = {"-mf"}, paramLabel = "<Mapping File>", description = "Iriusrisk Mapping File") String mapping,
          @CommandLine.Option(names = {"-p"}, paramLabel = "<Parameters>", description = "Template parameters") String parameters) {

    CredentialUtils.checkToken(spec);

    System.out.println("name " + name);
    System.out.println("id " + id);
    System.out.println("template " + template);
    System.out.println("mapping " + mapping);
    System.out.println("parameters " + parameters);

    try {

      CfImport cfImport = new CfImport();
      cfImport.setTemplateFileName(template);
      if (mapping != null && !mapping.isEmpty()) {
        cfImport.setMappingFileName(mapping);
      } else {
        cfImport.setMappingFileName(Irius.getIriusPath() + "cf-iriusrisk-mapping.yaml");
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

      System.out.println("ps.toString() before ");

      ProductShort ps = api.productsUploadPost(token, id, name, new File(Irius.getIriusPath() + "/" + "cf-iriusrisk-product.xml"), "STANDARD");
      System.out.println("ps.toString() " + ps.toString());

      api.rulesProductRefPut(token, id, "false");

      //This will call https://app.swaggerhub.com/apis/iriusrisk/IriusRisk/1#/Products/post_products_upload
      //to create a new product with the generated draw.io diagram embedded. 
      //AND it should call the API: 
      //https://app.swaggerhub.com/apis/iriusrisk/IriusRisk/1#/Products/put_rules_product__ref_ 
      //which will generate the model associated with the draw.io diagram.
      //should look in the folder ~/.irius for a file called cf-iriusrisk-mapping.yaml t
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
